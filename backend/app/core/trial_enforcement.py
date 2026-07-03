from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import uuid as _uuid

from app.models.org import User

TRIAL_QUERY_LIMIT = 10  # Single source of truth — exposed via /billing/status and used everywhere


async def check_and_increment_trial(user_id: str, db: AsyncSession) -> dict:
    """
    Checks trial quota and increments the counter atomically.

    Returns:
        {
            "allowed": bool,
            "queries_used": int | None,
            "queries_remaining": int | None,
            "plan": str,
        }

    Raises HTTP 402 if trial is exhausted (plan == "trial" and used >= limit).
    """
    # BUG-014 FIX: User.id is a UUID column. asyncpg's strict type checking
    # requires a uuid.UUID object, not a raw string, in the WHERE clause.
    try:
        user_uuid = _uuid.UUID(str(user_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid user ID format")

    result = await db.execute(select(User).where(User.id == user_uuid))

    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.plan != "trial":
        return {
            "allowed": True,
            "queries_used": None,
            "queries_remaining": None,
            "plan": user.plan,
        }

    if user.trial_queries_used >= TRIAL_QUERY_LIMIT:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "trial_exhausted",
                "message": f"Your free trial of {TRIAL_QUERY_LIMIT} queries is complete.",
                "queries_used": user.trial_queries_used,
                "trial_limit": TRIAL_QUERY_LIMIT,
                "upgrade_url": "/upgrade",
            },
        )

    await db.execute(
        update(User)
        .where(User.id == user_uuid)
        .values(trial_queries_used=User.trial_queries_used + 1)
    )
    await db.commit()

    new_count = user.trial_queries_used + 1
    return {
        "allowed": True,
        "queries_used": new_count,
        "queries_remaining": TRIAL_QUERY_LIMIT - new_count,
        "plan": "trial",
    }
