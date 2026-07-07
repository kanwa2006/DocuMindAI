import logging
import uuid
from datetime import datetime, timedelta

import redis as redis_lib
from celery import shared_task
from sqlalchemy import select, update

from app.core.config import settings
from app.db.session import SyncSessionLocal
from app.models.org import User
from app.services.email_service import send_email

logger = logging.getLogger(__name__)


def _renewal_html(user: User) -> str:
    ends = user.subscription_ends_at.strftime("%B %d, %Y")
    return f"""<html><body style="font-family:Arial,sans-serif;padding:24px;max-width:600px;">
<h2 style="color:#5b4fcf;">Subscription Renewal Reminder</h2>
<p>Hi {user.full_name or 'there'},</p>
<p>Your <b>{user.plan}</b> subscription expires on <b>{ends}</b> — 3 days from now.</p>
<p>Your access and all your documents will continue automatically upon renewal.</p>
<a href="{settings.FRONTEND_URL}/billing"
   style="display:inline-block;background:#5b4fcf;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;">
  Manage Subscription →
</a>
</body></html>"""


def _expired_html(user: User) -> str:
    return f"""<html><body style="font-family:Arial,sans-serif;padding:24px;max-width:600px;">
<h2 style="color:#dc2626;">Your Subscription Has Expired</h2>
<p>Hi {user.full_name or 'there'},</p>
<p>Your <b>{user.plan}</b> subscription has expired. Your account is now on the free trial tier —
   all your documents and history are preserved.</p>
<a href="{settings.FRONTEND_URL}/pricing"
   style="display:inline-block;background:#5b4fcf;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;">
  Re-subscribe →
</a>
</body></html>"""


def _grace_html(user: User) -> str:
    return f"""<html><body style="font-family:Arial,sans-serif;padding:24px;max-width:600px;">
<h2 style="color:#f59e0b;">Payment Failed — 48-Hour Grace Period</h2>
<p>Hi {user.full_name or 'there'},</p>
<p>We could not process payment for your DocuMindAI subscription.
   You have a <b>48-hour grace period</b> to update your payment details.</p>
<a href="{settings.FRONTEND_URL}/billing"
   style="display:inline-block;background:#f59e0b;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;">
  Update Payment →
</a>
<p style="color:#6b7280;font-size:13px;margin-top:16px;">
  If not resolved within 48 hours, your account will be downgraded to the free tier
  (all data preserved).
</p>
</body></html>"""


@shared_task(name="app.automation.auto_subscription_check.run_subscription_check")
def run_subscription_check():
    now = datetime.utcnow()
    three_days = now + timedelta(days=3)
    window_start = three_days - timedelta(hours=1)
    window_end = three_days + timedelta(hours=1)

    with SyncSessionLocal() as db:
        # 1. Renewal reminders — subscriptions expiring in ~3 days
        upcoming = db.execute(
            select(User).where(
                User.subscription_ends_at >= window_start,
                User.subscription_ends_at <= window_end,
                User.plan != "trial",
            )
        ).scalars().all()

        for user in upcoming:
            try:
                send_email(
                    to_email=user.email,
                    subject="Your DocuMindAI subscription renews in 3 days",
                    html_body=_renewal_html(user),
                )
                logger.info("[subscription_check] Renewal reminder sent to %s", user.email)
            except Exception as exc:
                logger.error("[subscription_check] Reminder failed for %s: %s", user.email, exc)

        # 2. Downgrade expired subscriptions to trial (data preserved)
        expired = db.execute(
            select(User).where(
                User.subscription_ends_at < now,
                User.plan != "trial",
            )
        ).scalars().all()

        for user in expired:
            old_plan = user.plan
            try:
                db.execute(update(User).where(User.id == user.id).values(plan="trial"))
                send_email(
                    to_email=user.email,
                    subject="Your DocuMindAI subscription has expired",
                    html_body=_expired_html(user),
                )
                logger.info(
                    "[subscription_check] Downgraded %s: %s → trial", user.email, old_plan
                )
            except Exception as exc:
                logger.error("[subscription_check] Downgrade failed for %s: %s", user.email, exc)

        db.commit()

        # 3. Payment grace period reminders — IDs are added to Redis by payment webhooks
        try:
            _redis = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
            grace_ids = _redis.smembers("payment_grace_users")

            for uid_str in grace_ids:
                try:
                    user = db.execute(
                        select(User).where(User.id == uuid.UUID(uid_str))
                    ).scalar_one_or_none()
                    if user:
                        send_email(
                            to_email=user.email,
                            subject="Action needed: Payment failed — 48-hour grace period",
                            html_body=_grace_html(user),
                        )
                        _redis.srem("payment_grace_users", uid_str)
                        logger.info(
                            "[subscription_check] Grace reminder sent to %s", user.email
                        )
                except Exception as exc:
                    logger.error(
                        "[subscription_check] Grace reminder failed for %s: %s", uid_str, exc
                    )
        except Exception as exc:
            logger.error("[subscription_check] Payment grace check error: %s", exc)
