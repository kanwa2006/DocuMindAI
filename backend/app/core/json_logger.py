"""
JSON structured logger for production. Plain string logs are used in dev.

Activated via ENVIRONMENT=production (default in `setup_logging`).

PII (email/phone/SSN) is stripped via `app.utils.pii_redactor.redact_pii`.
Correlation IDs are taken from `CorrelationIdMiddleware` and attached via
`record.request_id` if present.

Usage: setup_logging() in main.py wires this in.
"""
import json
import logging
import sys
from typing import Any

from app.utils.pii_redactor import redact_pii


class JSONFormatter(logging.Formatter):
    """Emits a single JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": redact_pii(record.getMessage()),
        }
        # Correlation IDs from CorrelationIdMiddleware
        for attr in ("request_id", "user_id", "workspace_id"):
            value = getattr(record, attr, None)
            if value is not None:
                payload[attr] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def build_json_handler() -> logging.Handler:
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JSONFormatter())
    return handler
