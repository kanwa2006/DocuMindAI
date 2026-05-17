import logging
import sys

def setup_logging():
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    # Silence third-party chatty logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
