import logging
import os
from datetime import datetime

import redis as redis_lib
from celery import shared_task

from app.core.config import settings
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

_redis = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
KEY_STATUS_HASH = "api_key_status"


def _test_api_key(key: str) -> str:
    try:
        # S5: THIS was the worst global writer. It walks EVERY key testing
        # each one, and `genai.configure` left the process global set to
        # whichever key it happened to test last — in the same worker process
        # as embedding_service. A per-key client tests exactly the key it was
        # asked about and affects nothing else.
        from google.genai import types as genai_types
        from app.services.gemini_client import get_client_pool

        get_client_pool().client_for(key).models.generate_content(
            model=settings.GEMINI_MODEL,
            contents="test",
            config=genai_types.GenerateContentConfig(max_output_tokens=1),
        )
        return "pass"
    except Exception as exc:
        err = str(exc)
        if "404" in err or "deprecated" in err.lower():
            return "deprecated"
        if "403" in err or "invalid" in err.lower():
            return "invalid"
        if "429" in err or "quota" in err.lower():
            return "rate_limited"
        return "error"


@shared_task(name="app.automation.auto_key_rotation.check_api_keys")
def check_api_keys():
    results = {}

    i = 1
    while True:
        key = os.environ.get(f"GEMINI_API_KEY_{i}")
        if not key or not key.strip():
            break
        label = f"key_{i}"
        status = _test_api_key(key.strip())
        _redis.hset(KEY_STATUS_HASH, label, status)
        results[label] = status
        logger.info("[key_rotation] %s: %s", label, status)
        i += 1

    # Legacy single-key support
    single = os.environ.get("GEMINI_API_KEY")
    if single and single.strip():
        status = _test_api_key(single.strip())
        _redis.hset(KEY_STATUS_HASH, "key_legacy", status)
        results["key_legacy"] = status

    _redis.hset(KEY_STATUS_HASH, "last_checked", datetime.utcnow().isoformat())

    passing = [k for k, s in results.items() if s == "pass"]
    failing = {k: s for k, s in results.items() if s != "pass"}

    if not passing and results:
        logger.error("[key_rotation] ALL keys failing: %s", failing)
        admin = settings.ADMIN_EMAIL
        if admin:
            items = "".join(f"<li><b>{k}</b>: {v}</li>" for k, v in failing.items())
            send_email(
                to_email=admin,
                subject="CRITICAL: All Gemini API keys are failing — DocuMindAI down",
                html_body=f"""<html><body style="font-family:Arial,sans-serif;padding:24px;">
<h2 style="color:#dc2626;">All Gemini API Keys Failing</h2>
<p>Checked: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
<ul>{items}</ul>
<p>DocuMindAI cannot process queries. Add valid keys to .env and restart.</p>
</body></html>""",
            )
    else:
        logger.info("[key_rotation] %d/%d keys passing", len(passing), len(results))
