import logging
import os
import sys


def setup_logging():
    """
    Plain text logs in dev (human-readable). JSON structured logs in prod
    (machine-parseable; ELK / Datadog / Loki ingest cleanly).

    The JSON formatter PII-redacts emails / phone / SSN and includes
    correlation IDs attached by CorrelationIdMiddleware.
    """
    is_prod = os.getenv("ENVIRONMENT", "development") == "production"

    root = logging.getLogger()
    # Reset any prior handlers so re-imports during dev don't double-attach.
    for h in list(root.handlers):
        root.removeHandler(h)

    if is_prod:
        # STEP 14 — structured JSON pipeline
        from app.core.json_logger import build_json_handler
        root.addHandler(build_json_handler())
    else:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        root.addHandler(handler)

    root.setLevel(logging.INFO)
    # Silence third-party chatty logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
