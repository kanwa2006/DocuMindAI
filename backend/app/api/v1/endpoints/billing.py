from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update as sa_update

from app.db.session import get_db
from app.models.org import User
from app.core.auth import get_current_user
from app.core.trial_enforcement import TRIAL_QUERY_LIMIT

router = APIRouter()


class UpgradeRequest(BaseModel):
    # W1 (deep-debug session 4): three new ChatGPT-style tiers — "go" / "plus" /
    # "pro" — added alongside the legacy {professional,business,enterprise}
    # names. The DB still stores whatever string we set; old plans remain
    # readable so we don't break existing subscriptions.
    plan: Literal["go", "plus", "pro", "professional", "business", "enterprise"] = "plus"
    billing_cycle: Literal["monthly", "annual"] = "monthly"


@router.post("/upgrade")
async def upgrade_plan(
    body: UpgradeRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Placeholder upgrade endpoint.
    In production: validate Razorpay/Stripe webhook instead of direct call.
    """
    user_id = current_user["id"]

    now = datetime.utcnow()
    days = 365 if body.billing_cycle == "annual" else 30
    ends_at = now + timedelta(days=days)

    await db.execute(
        sa_update(User)
        .where(User.id == user_id)
        .values(
            plan=body.plan,
            subscribed_at=now,
            subscription_ends_at=ends_at,
        )
    )
    await db.commit()

    return {
        "success": True,
        "plan": body.plan,
        "billing_cycle": body.billing_cycle,
        "subscribed_at": now.isoformat(),
        "subscription_ends_at": ends_at.isoformat(),
        "message": "Subscription activated",
    }


@router.get("/status")
async def billing_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns current plan, trial counter, and subscription window."""
    user_id = current_user["id"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    remaining = (
        max(TRIAL_QUERY_LIMIT - user.trial_queries_used, 0)
        if user.plan == "trial"
        else None
    )

    return {
        "plan": user.plan,
        "trial_queries_used": user.trial_queries_used,
        "trial_limit": TRIAL_QUERY_LIMIT,
        "queries_remaining": remaining,
        "email_verified": user.email_verified,
        "subscribed_at": user.subscribed_at.isoformat() if user.subscribed_at else None,
        "subscription_ends_at": user.subscription_ends_at.isoformat() if user.subscription_ends_at else None,
    }
