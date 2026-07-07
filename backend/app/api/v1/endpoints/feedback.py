import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.feedback import Feedback
from app.core.auth import get_optional_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

RATE_LIMIT_MAX = 3
RATE_LIMIT_WINDOW = 3600  # 1 hour


class FeedbackRequest(BaseModel):
    type: str
    message: str
    email: Optional[str] = None
    page_url: Optional[str] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"Bug Report", "Feature Request", "General Feedback", "Payment Issue"}
        if v not in allowed:
            raise ValueError(f"type must be one of {allowed}")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if len(v.strip()) < 20:
            raise ValueError("message must be at least 20 characters")
        return v.strip()


async def _get_redis():
    try:
        import aioredis
        return await aioredis.from_url(
            __import__("app.core.config", fromlist=["settings"]).settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    except Exception:
        return None


async def _check_feedback_rate_limit(rate_key: str) -> None:
    redis = await _get_redis()
    if not redis:
        return
    try:
        key = f"feedback_rl:{rate_key}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, RATE_LIMIT_WINDOW)
        if count > RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=429,
                detail="Too many feedback submissions. Please wait an hour before trying again.",
            )
    finally:
        await redis.close()


@router.post("/feedback", status_code=201)
async def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    current_user: Optional[dict] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Submit help or feedback. Works for both authenticated and unauthenticated users.
    Rate limited to 3 submissions per hour per user/IP.
    """
    # Determine rate-limit key: prefer user_id, fall back to IP
    if current_user:
        rate_key = f"user:{current_user['id']}"
    else:
        client_ip = request.headers.get("X-Forwarded-For", "")
        client_ip = client_ip.split(",")[0].strip() if client_ip else (
            request.client.host if request.client else "unknown"
        )
        rate_key = f"ip:{client_ip}"

    await _check_feedback_rate_limit(rate_key)

    entry = Feedback(
        user_id=current_user["id"] if current_user else None,
        type=body.type,
        message=body.message,
        email=body.email,
        user_plan=current_user.get("plan") if current_user else None,
        page_url=body.page_url,
    )
    db.add(entry)
    await db.commit()

    logger.info(
        "[feedback] type=%s user_id=%s",
        body.type,
        current_user["id"] if current_user else "anonymous",
    )

    return {"success": True, "message": "Feedback received. Thank you!"}
