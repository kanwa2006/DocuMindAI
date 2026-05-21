import logging
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


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = str(current_user["id"])
    result = await db.execute(select(User).where(User.id == user_id))
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
    user_id = str(current_user["id"])

    if payload.preferred_language is not None:
        lang = payload.preferred_language.lower().strip()
        if lang not in VALID_LANGUAGES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid language '{lang}'. Valid values: {sorted(VALID_LANGUAGES)}",
            )
        await db.execute(
            sa_update(User)
            .where(User.id == user_id)
            .values(preferred_language=lang)
        )
        await db.commit()

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        preferred_language=user.preferred_language or "auto",
    )
