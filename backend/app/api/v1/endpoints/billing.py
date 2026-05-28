"""
billing.py — DocuMindAI subscription & payment endpoints.

Razorpay integration is gated behind RAZORPAY_ENABLED=true so local
development works without payment credentials (falls back to direct
DB update in sandbox/dev environments only).

Production flow:
  1. POST /billing/create-order  → returns Razorpay order_id + key
  2. Frontend opens Razorpay checkout
  3. Razorpay calls POST /billing/webhook on payment success
  4. Webhook verifies HMAC signature → upgrades DB plan
"""
import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update as sa_update

from app.db.session import get_db
from app.models.org import User
from app.core.auth import get_current_user
from app.core.trial_enforcement import TRIAL_QUERY_LIMIT

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Razorpay feature flag ─────────────────────────────────────────────────────
RAZORPAY_ENABLED: bool = os.getenv("RAZORPAY_ENABLED", "false").lower() == "true"
RAZORPAY_KEY_ID: Optional[str] = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET: Optional[str] = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET: Optional[str] = os.getenv("RAZORPAY_WEBHOOK_SECRET")

# ── Plan → price map (INR paise: 1 INR = 100 paise) ──────────────────────────
PLAN_PRICES_INR = {
    # plan_name: { "monthly": paise, "annual": paise }
    "go":           {"monthly": 79900,  "annual": 767040},   # ₹799 / ₹7,670.40
    "plus":         {"monthly": 99900,  "annual": 959040},   # ₹999 / ₹9,590.40
    "pro":          {"monthly": 299900, "annual": 2879040},  # ₹2999 / ₹28,790.40
    "professional": {"monthly": 299900, "annual": 2879040},
    "business":     {"monthly": 299900, "annual": 2879040},
    "enterprise":   {"monthly": 299900, "annual": 2879040},
}


def _days_for_cycle(billing_cycle: str) -> int:
    return 365 if billing_cycle == "annual" else 30


# ── Request / response schemas ────────────────────────────────────────────────
class UpgradeRequest(BaseModel):
    plan: Literal["go", "plus", "pro", "professional", "business", "enterprise"] = "plus"
    billing_cycle: Literal["monthly", "annual"] = "monthly"


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int        # paise
    currency: str
    razorpay_key: str
    plan: str
    billing_cycle: str


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _activate_plan(user_id: str, plan: str, billing_cycle: str, db: AsyncSession) -> dict:
    """Atomically sets plan + subscription window on the user row."""
    now = datetime.utcnow()
    ends_at = now + timedelta(days=_days_for_cycle(billing_cycle))
    await db.execute(
        sa_update(User)
        .where(User.id == user_id)
        .values(plan=plan, subscribed_at=now, subscription_ends_at=ends_at)
    )
    await db.commit()
    return {
        "success": True,
        "plan": plan,
        "billing_cycle": billing_cycle,
        "subscribed_at": now.isoformat(),
        "subscription_ends_at": ends_at.isoformat(),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/create-order", response_model=CreateOrderResponse)
async def create_razorpay_order(
    body: UpgradeRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Creates a Razorpay order and returns the order_id to the frontend.
    Requires RAZORPAY_ENABLED=true and valid Razorpay credentials.
    """
    if not RAZORPAY_ENABLED:
        raise HTTPException(
            status_code=501,
            detail="Payment gateway not configured. Set RAZORPAY_ENABLED=true and credentials.",
        )
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=500, detail="Razorpay credentials missing.")

    try:
        import razorpay  # type: ignore
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    except ImportError:
        raise HTTPException(status_code=500, detail="razorpay package not installed.")

    amount = PLAN_PRICES_INR[body.plan][body.billing_cycle]
    receipt = f"docuMind_{current_user['id']}_{body.plan}"[:40]

    try:
        order = client.order.create(
            {
                "amount": amount,
                "currency": "INR",
                "receipt": receipt,
                "notes": {
                    "user_id": str(current_user["id"]),
                    "plan": body.plan,
                    "billing_cycle": body.billing_cycle,
                },
            }
        )
    except Exception as e:
        logger.error(f"[Billing] Razorpay order creation failed: {e}")
        raise HTTPException(status_code=502, detail="Could not create payment order.")

    return CreateOrderResponse(
        order_id=order["id"],
        amount=amount,
        currency="INR",
        razorpay_key=RAZORPAY_KEY_ID,
        plan=body.plan,
        billing_cycle=body.billing_cycle,
    )


@router.post("/webhook")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Razorpay payment webhook — verifies HMAC-SHA256 signature then upgrades plan.
    Set this URL in Razorpay Dashboard → Webhooks → payment.captured.
    """
    if not RAZORPAY_ENABLED or not RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(status_code=501, detail="Webhook not configured.")

    body_bytes = await request.body()
    received_sig = request.headers.get("X-Razorpay-Signature", "")

    expected_sig = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, received_sig):
        logger.warning("[Billing] Razorpay webhook HMAC mismatch — rejecting.")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    import json
    payload = json.loads(body_bytes)
    event = payload.get("event")

    if event != "payment.captured":
        # Acknowledge non-captured events without processing
        return {"status": "ignored", "event": event}

    try:
        notes = payload["payload"]["payment"]["entity"]["notes"]
        user_id: str = notes["user_id"]
        plan: str = notes["plan"]
        billing_cycle: str = notes.get("billing_cycle", "monthly")
    except (KeyError, TypeError) as e:
        logger.error(f"[Billing] Webhook payload missing notes: {e}")
        raise HTTPException(status_code=422, detail="Webhook payload malformed")

    result = await _activate_plan(user_id, plan, billing_cycle, db)
    logger.info(f"[Billing] Plan activated via webhook: user={user_id} plan={plan}")
    return {"status": "ok", **result}


@router.post("/upgrade")
async def upgrade_plan(
    body: UpgradeRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Direct upgrade endpoint.

    • If RAZORPAY_ENABLED=true  → returns 402 instructing the client to use
      /billing/create-order instead (prevents bypassing payment in production).
    • If RAZORPAY_ENABLED=false → activates plan directly (dev / sandbox mode).
    """
    if RAZORPAY_ENABLED:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "payment_required",
                "message": "Use POST /billing/create-order to initiate Razorpay checkout.",
                "create_order_url": "/billing/create-order",
            },
        )

    # Dev / sandbox path — flip the plan directly (no payment needed)
    logger.info(
        f"[Billing] Sandbox upgrade: user={current_user['id']} → {body.plan} ({body.billing_cycle})"
    )
    result = await _activate_plan(current_user["id"], body.plan, body.billing_cycle, db)
    return {**result, "message": "Subscription activated (sandbox mode — no payment charged)"}


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
        "subscription_ends_at": (
            user.subscription_ends_at.isoformat() if user.subscription_ends_at else None
        ),
        "razorpay_enabled": RAZORPAY_ENABLED,
        "razorpay_key_id": RAZORPAY_KEY_ID if RAZORPAY_ENABLED else None,
    }
