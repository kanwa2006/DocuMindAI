import logging
from datetime import datetime, timedelta

from celery import shared_task
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import SyncSessionLocal
from app.models.chat import ChatMessage, ChatSession
from app.models.feedback import Feedback
from app.models.org import User
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

PLAN_MONTHLY_PRICE = {
    "professional": 499,
    "team": 999,
    "enterprise": 4999,
}


@shared_task(name="app.automation.auto_daily_digest.send_daily_digest")
def send_daily_digest():
    admin = settings.ADMIN_EMAIL
    if not admin:
        logger.warning("[daily_digest] ADMIN_EMAIL not configured — skipping")
        return

    since = datetime.utcnow() - timedelta(hours=24)
    today = datetime.utcnow().strftime("%Y-%m-%d")

    try:
        with SyncSessionLocal() as db:
            new_signups = db.execute(
                select(func.count(User.id)).where(User.created_at >= since)
            ).scalar() or 0

            conversions = db.execute(
                select(func.count(User.id)).where(
                    User.subscribed_at >= since,
                    User.plan != "trial",
                )
            ).scalar() or 0

            total_queries = db.execute(
                select(func.count(ChatMessage.id)).where(
                    ChatMessage.role == "user",
                    ChatMessage.created_at >= since,
                )
            ).scalar() or 0

            unique_users = db.execute(
                select(func.count(func.distinct(ChatSession.owner_id))).where(
                    ChatSession.updated_at >= since
                )
            ).scalar() or 0

            new_subscribers = db.execute(
                select(User.plan).where(
                    User.subscribed_at >= since,
                    User.plan.in_(list(PLAN_MONTHLY_PRICE.keys())),
                )
            ).scalars().all()
            new_mrr = sum(PLAN_MONTHLY_PRICE.get(p, 0) for p in new_subscribers)

            new_feedback = db.execute(
                select(func.count(Feedback.id)).where(Feedback.created_at >= since)
            ).scalar() or 0

            top_ws_row = db.execute(
                select(ChatSession.workspace_type, func.count(ChatMessage.id).label("cnt"))
                .join(ChatMessage, ChatMessage.session_id == ChatSession.id)
                .where(ChatMessage.created_at >= since, ChatMessage.role == "user")
                .group_by(ChatSession.workspace_type)
                .order_by(func.count(ChatMessage.id).desc())
                .limit(1)
            ).first()
            top_workspace = f"{top_ws_row[0]} ({top_ws_row[1]} queries)" if top_ws_row else "N/A"

    except Exception as exc:
        logger.error("[daily_digest] DB query failed: %s", exc)
        return

    subject = f"DocuMindAI Daily Digest — {today} — {new_signups} users, ₹{new_mrr} MRR"
    html = f"""<html><body style="font-family:Arial,sans-serif;color:#1a1a1a;padding:24px;max-width:600px;">
<h2 style="color:#5b4fcf;">DocuMindAI Daily Digest</h2>
<p style="color:#6b7280;">{today} (last 24 hours)</p>
<table style="border-collapse:collapse;width:100%;">
  <tr style="background:#f3f0ff;"><td style="padding:10px;font-weight:bold;">New Signups</td><td style="padding:10px;">{new_signups}</td></tr>
  <tr><td style="padding:10px;font-weight:bold;">Trial → Paid Conversions</td><td style="padding:10px;">{conversions}</td></tr>
  <tr style="background:#f3f0ff;"><td style="padding:10px;font-weight:bold;">Total Queries</td><td style="padding:10px;">{total_queries}</td></tr>
  <tr><td style="padding:10px;font-weight:bold;">Unique Active Users</td><td style="padding:10px;">{unique_users}</td></tr>
  <tr style="background:#f3f0ff;"><td style="padding:10px;font-weight:bold;">New MRR</td><td style="padding:10px;">₹{new_mrr:,}</td></tr>
  <tr><td style="padding:10px;font-weight:bold;">New Feedback Submissions</td><td style="padding:10px;">{new_feedback}</td></tr>
  <tr style="background:#f3f0ff;"><td style="padding:10px;font-weight:bold;">Top Workspace</td><td style="padding:10px;">{top_workspace}</td></tr>
</table>
<p style="color:#9ca3af;font-size:12px;margin-top:24px;">DocuMindAI — Automated Daily Report</p>
</body></html>"""

    send_email(to_email=admin, subject=subject, html_body=html)
    logger.info("[daily_digest] Sent digest to %s", admin)
