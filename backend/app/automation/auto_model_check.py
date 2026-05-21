import logging
from datetime import datetime

import redis as redis_lib
from celery import shared_task

from app.core.config import settings
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

_redis = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
MODEL_OVERRIDE_KEY = "gemini_model_override"


def _is_deprecation_error(exc: Exception) -> bool:
    err = str(exc)
    lower = err.lower()
    return (
        "404" in err
        or "deprecated" in lower
        or ("model" in lower and ("not found" in lower or "invalid" in lower or "unsupported" in lower))
    )


@shared_task(name="app.automation.auto_model_check.check_model_status")
def check_model_status():
    current_model = settings.GEMINI_MODEL
    fallback_model = settings.GEMINI_FALLBACK_MODEL
    admin = settings.ADMIN_EMAIL

    try:
        import google.generativeai as genai
        from app.services.llm_key_rotation import get_key_rotator
        key = get_key_rotator().get_key()
        genai.configure(api_key=key)
        model = genai.GenerativeModel(current_model)
        model.generate_content("test", generation_config={"max_output_tokens": 1})
        _redis.delete(MODEL_OVERRIDE_KEY)
        logger.info("[model_check] %s is healthy", current_model)

    except Exception as exc:
        if not _is_deprecation_error(exc):
            logger.warning("[model_check] Non-deprecation error for %s: %s", current_model, exc)
            return

        logger.critical(
            "[model_check] Model %s deprecated/unavailable: %s — switching to fallback %s",
            current_model, exc, fallback_model,
        )

        # Store override in Redis so operators can see the switch
        _redis.set(MODEL_OVERRIDE_KEY, fallback_model)

        if admin:
            send_email(
                to_email=admin,
                subject="CRITICAL: Gemini model deprecated — auto-switched to fallback",
                html_body=f"""<html><body style="font-family:Arial,sans-serif;padding:24px;max-width:600px;">
<h2 style="color:#dc2626;">Model Deprecation Alert</h2>
<p>Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
<p>Model <b>{current_model}</b> returned a deprecation or 404 error.</p>
<p><b>Action taken:</b> Fallback model <b>{fallback_model}</b> stored in Redis key
   <code>{MODEL_OVERRIDE_KEY}</code>.</p>
<p><b>Required action:</b> Update <code>GEMINI_MODEL={fallback_model}</code> in your
   <code>.env</code> file and restart the application to make this permanent.</p>
<p style="color:#6b7280;font-size:13px;">Error: {str(exc)[:300]}</p>
</body></html>""",
            )
