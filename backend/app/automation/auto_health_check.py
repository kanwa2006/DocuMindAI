import logging
import os
import shutil
from datetime import datetime

import redis as redis_lib
from celery import shared_task
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SyncSessionLocal
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

_redis = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
FAIL_STREAK_KEY = "health_fail_streak"
ALERT_THRESHOLD = 3


def _check_db():
    try:
        with SyncSessionLocal() as db:
            db.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as exc:
        return False, str(exc)[:200]


def _check_redis():
    try:
        _redis.ping()
        return True, "ok"
    except Exception as exc:
        return False, str(exc)[:200]


def _check_gemini():
    try:
        import google.generativeai as genai
        from app.services.llm_key_rotation import get_key_rotator
        key = get_key_rotator().get_key()
        genai.configure(api_key=key)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        model.generate_content("hi", generation_config={"max_output_tokens": 1})
        return True, "ok"
    except Exception as exc:
        return False, str(exc)[:200]


def _check_disk():
    try:
        path = settings.STORAGE_PATH if os.path.exists(settings.STORAGE_PATH) else "."
        usage = shutil.disk_usage(path)
        pct = usage.used / usage.total * 100
        if pct > 90:
            return False, f"Disk {pct:.1f}% used (>90% threshold)"
        return True, f"{pct:.1f}% used"
    except Exception as exc:
        return False, str(exc)[:200]


def _check_celery():
    try:
        from app.workers.celery_app import celery_app
        ping = celery_app.control.ping(timeout=3)
        if not ping:
            return False, "No workers responded to ping"
        return True, f"{len(ping)} worker(s) active"
    except Exception as exc:
        return False, str(exc)[:200]


@shared_task(name="app.automation.auto_health_check.run_health_check")
def run_health_check():
    checks = {
        "database": _check_db(),
        "redis": _check_redis(),
        "gemini_api": _check_gemini(),
        "disk": _check_disk(),
        "celery_worker": _check_celery(),
    }

    failures = {name: msg for name, (ok, msg) in checks.items() if not ok}

    if failures:
        logger.error("[health_check] %d check(s) failed: %s", len(failures), failures)
        streak = int(_redis.incr(FAIL_STREAK_KEY))
        _redis.expire(FAIL_STREAK_KEY, 7200)

        if streak >= ALERT_THRESHOLD:
            admin = settings.ADMIN_EMAIL
            if admin:
                items = "".join(f"<li><b>{k}</b>: {v}</li>" for k, v in failures.items())
                send_email(
                    to_email=admin,
                    subject=f"ALERT: DocuMindAI health check — {streak} consecutive failures",
                    html_body=f"""<html><body style="font-family:Arial,sans-serif;padding:24px;">
<h2 style="color:#dc2626;">Health Check Alert</h2>
<p>Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
<p><b>{streak} consecutive failures</b> detected:</p>
<ul>{items}</ul>
<p>Please investigate immediately.</p>
</body></html>""",
                )
            _redis.delete(FAIL_STREAK_KEY)
    else:
        _redis.delete(FAIL_STREAK_KEY)
        logger.info("[health_check] All checks passed")


health_check_task = run_health_check  # alias for external imports
