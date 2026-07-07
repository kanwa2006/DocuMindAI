import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update as sa_update
from typing import Optional

from app.db.session import get_db
from app.models.org import User
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_LANGUAGES = {
    "auto", "english", "hindi", "tamil", "telugu",
    "kannada", "malayalam", "gujarati", "marathi", "bengali",
}


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    preferred_language: str


class UserProfileUpdate(BaseModel):
    preferred_language: Optional[str] = None


def _coerce_user_id(raw: str) -> uuid.UUID:
    """P4: User.id is a postgres UUID column. asyncpg + SQLAlchemy don't
    always implicit-cast string → UUID, and the failure surfaces as a 500
    that the frontend renders as 'Failed to fetch' on the settings save.
    Cast once here so every query that follows is type-safe.
    """
    try:
        return uuid.UUID(str(raw))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid user id in token.")


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_uuid = _coerce_user_id(current_user["id"])
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        preferred_language=user.preferred_language or "auto",
    )


@router.patch("/me", response_model=UserProfileResponse)
async def patch_me(
    payload: UserProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_uuid = _coerce_user_id(current_user["id"])

    if payload.preferred_language is not None:
        lang = payload.preferred_language.lower().strip()
        if lang not in VALID_LANGUAGES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid language '{lang}'. Valid values: {sorted(VALID_LANGUAGES)}",
            )
        try:
            await db.execute(
                sa_update(User)
                .where(User.id == user_uuid)
                .values(preferred_language=lang)
            )
            await db.commit()
        except Exception as exc:
            # P4: surface a real 500 with a meaningful body so the frontend
            # doesn't show "Failed to fetch" when the connection dies
            # mid-flight. Roll back so the next request sees a clean state.
            await db.rollback()
            logger.error(f"[users/me PATCH] DB update failed: {exc}")
            raise HTTPException(
                status_code=500,
                detail="Could not save preferences. Please try again.",
            )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        preferred_language=user.preferred_language or "auto",
    )
