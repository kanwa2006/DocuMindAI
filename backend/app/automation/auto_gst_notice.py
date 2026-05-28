import logging
from datetime import datetime

import redis as redis_lib
from celery import shared_task

from app.core.config import settings
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

_redis = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
GST_LAST_UPDATED_KEY = "gst_last_updated"
STALE_DAYS = 90


@shared_task(name="app.automation.auto_gst_notice.check_gst_rates")
def check_gst_rates():
    admin = settings.ADMIN_EMAIL
    if not admin:
        logger.warning("[gst_notice] ADMIN_EMAIL not configured — skipping")
        return

    last_str = _redis.get(GST_LAST_UPDATED_KEY)

    if not last_str:
        last_display = "Never recorded"
        is_stale = True
    else:
        try:
            last_dt = datetime.fromisoformat(last_str)
            age_days = (datetime.utcnow() - last_dt).days
            last_display = last_dt.strftime("%Y-%m-%d")
            is_stale = age_days >= STALE_DAYS
        except ValueError:
            last_display = last_str
            is_stale = True

    if is_stale:
        logger.warning("[gst_notice] GST rates stale — last updated: %s", last_display)
        today_iso = datetime.utcnow().date().isoformat()
        send_email(
            to_email=admin,
            subject=f"Action needed: GST rates may be outdated — last updated {last_display}",
            html_body=f"""<html><body style="font-family:Arial,sans-serif;padding:24px;max-width:600px;">
<h2 style="color:#f59e0b;">GST Rate Review Reminder</h2>
<p>Your GST rate table was last updated: <b>{last_display}</b></p>
<p>It has been <b>{STALE_DAYS}+ days</b> since the last review. Please verify your GST rates
   against the latest government notifications.</p>
<p>After verifying, mark as current by running:<br>
<code style="background:#f3f4f6;padding:4px 8px;border-radius:4px;display:inline-block;margin-top:6px;">
redis-cli SET {GST_LAST_UPDATED_KEY} "{today_iso}"
</code></p>
<p style="color:#6b7280;font-size:13px;">
  Automated reminder only — no automatic changes have been made.
</p>
</body></html>""",
        )
    else:
        logger.info("[gst_notice] GST rates current — last updated: %s", last_display)
