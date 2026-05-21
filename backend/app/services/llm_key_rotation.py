import os
import threading
import time
import logging
from typing import List, Optional
from itertools import cycle

logger = logging.getLogger(__name__)

class GeminiKeyRotator:
    """
    Dynamically reads ALL GEMINI_API_KEY_N keys from environment.
    Rotates round-robin. Handles 429 (rate limit) and 403 (invalid key).
    Thread-safe. Singleton pattern.

    .env pattern: GEMINI_API_KEY_1, GEMINI_API_KEY_2, ... (any count)
    Also accepts GEMINI_API_KEY (single key, legacy support).
    """

    def __init__(self):
        self._keys: List[str] = []
        self._bad_keys: set = set()      # permanently skip these (403)
        self._cooling_keys: dict = {}    # key → cooldown_until timestamp (429)
        self._lock = threading.Lock()
        self._cycle = None
        self._load_keys()

    def _load_keys(self):
        """
        Reads keys from environment. Supports:
          GEMINI_API_KEY_1, GEMINI_API_KEY_2, ... (recommended, unlimited)
          GEMINI_API_KEY (single key, legacy)
        """
        keys = []

        # Read numbered keys (GEMINI_API_KEY_1, _2, _3, ...)
        i = 1
        while True:
            key = os.environ.get(f"GEMINI_API_KEY_{i}")
            if key and key.strip():
                keys.append(key.strip())
                i += 1
            else:
                break  # Stop at first missing number — no need to scan further

        # Also read GEMINI_API_KEY (single key legacy support)
        single = os.environ.get("GEMINI_API_KEY")
        if single and single.strip() and single.strip() not in keys:
            keys.append(single.strip())

        if not keys:
            raise RuntimeError(
                "No Gemini API keys found in environment. "
                "Set GEMINI_API_KEY_1 (and optionally GEMINI_API_KEY_2, _3, ...) in .env"
            )

        self._keys = keys
        self._cycle = cycle(keys)
        logger.info(f"GeminiKeyRotator loaded {len(keys)} API key(s)")

    def get_key(self) -> str:
        """
        Returns the next available API key.
        Skips: permanently bad keys (403), cooling-down keys (429).
        If ALL keys are unavailable, waits for the soonest cooldown to end.
        """
        with self._lock:
            now = time.time()
            available = [
                k for k in self._keys
                if k not in self._bad_keys
                and self._cooling_keys.get(k, 0) <= now
            ]

            if not available:
                # All keys cooling — wait for the soonest one
                soonest = min(self._cooling_keys.values())
                wait_time = max(0, soonest - now)
                logger.warning(f"All API keys cooling. Waiting {wait_time:.1f}s...")
                time.sleep(wait_time + 0.5)
                # Retry after wait
                available = [
                    k for k in self._keys
                    if k not in self._bad_keys
                ]

            if not available:
                raise RuntimeError(
                    "All API keys are invalid (403). "
                    "Add valid keys to .env and restart."
                )

            # Round-robin through available keys
            for _ in range(len(self._keys)):
                key = next(self._cycle)
                if key in available:
                    return key

            return available[0]  # Fallback

    def report_rate_limit(self, key: str, retry_after_seconds: int = 60):
        """Call this when Gemini returns 429. Cools down the key."""
        with self._lock:
            cooldown_until = time.time() + retry_after_seconds
            self._cooling_keys[key] = cooldown_until
            logger.warning(
                f"API key ...{key[-6:]} rate-limited. "
                f"Cooling for {retry_after_seconds}s."
            )

    def report_invalid_key(self, key: str):
        """Call this when Gemini returns 403. Permanently skips the key."""
        with self._lock:
            self._bad_keys.add(key)
            logger.error(
                f"API key ...{key[-6:]} is invalid (403). "
                f"Permanently skipping. {len(self._keys) - len(self._bad_keys)} "
                f"keys remaining."
            )

    @property
    def total_keys(self) -> int:
        return len(self._keys)

    @property
    def available_keys(self) -> int:
        now = time.time()
        return len([
            k for k in self._keys
            if k not in self._bad_keys
            and self._cooling_keys.get(k, 0) <= now
        ])

    @property
    def key_status(self) -> dict:
        """For /health endpoint — shows key health without exposing actual keys."""
        now = time.time()
        return {
            "total": self.total_keys,
            "available": self.available_keys,
            "cooling": len([k for k, t in self._cooling_keys.items() if t > now]),
            "invalid": len(self._bad_keys)
        }


# Singleton
_rotator_instance: Optional[GeminiKeyRotator] = None

def get_key_rotator() -> GeminiKeyRotator:
    global _rotator_instance
    if _rotator_instance is None:
        _rotator_instance = GeminiKeyRotator()
    return _rotator_instance
