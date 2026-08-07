"""Per-key Gemini clients — the replacement for global SDK configuration (S5).

## What was wrong

`genai.configure(api_key=...)` mutated PROCESS-GLOBAL state, and
`google.generativeai` resolved its client from that global **at call time**,
not when the model object was constructed. With concurrency >= 2:

    request A: configure(key 3) -> dispatch to executor
    request B: configure(key 7)
    request A's thread finally issues its HTTP call ... on KEY 7

If that call 429'd, the failure was attributed to key 3 and a **healthy key**
was cooled for 300 seconds while key 7 kept being handed out. Under load the
pool degraded progressively: healthy keys got cooled, hot keys never did, and
no log explained it.

Five modules wrote to that one global — the rotator, the embedding service,
and three Beat-scheduled automation jobs, across two process types. The worst
was `auto_key_rotation`, which deliberately walks every key and leaves the
global set to whichever it tested last, in the same process as the embedding
service.

## The fix

`google.genai.Client(api_key=...)` binds the key to the CLIENT. A request
selects a client and can only ever call with that client's key. There is no
window in which another request can change it, because nothing is mutated —
the binding is fixed at construction.

## Why clients are cached per key rather than built per request

Measured on this machine, against the installed `google-genai==2.5.0`:

    first Client()      3554.8 ms
    each subsequent     2456.9 ms

A client per request would add ~2.5 s to every LLM call. So there is exactly
one client per KEY, created lazily and reused. That keeps the property the
defect was about — **the api_key of a client is immutable, so there is no
shared mutable state to race on** — while multiple concurrent requests share a
healthy key's client, which is explicitly what the architecture calls for
("multiple users may simultaneously use the same healthy key; do not dedicate
one key per request").

## Concurrency

Client construction is guarded by a lock; the clients themselves are
independent and safe to use concurrently. Nothing here serialises requests:
the lock is held only while building a client the first time, never across a
network call.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, AsyncGenerator, Callable, Optional, Tuple

from app.services.llm_key_rotation import get_key_rotator

logger = logging.getLogger(__name__)

try:
    from google import genai as google_genai
    from google.genai import errors as genai_errors
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover - surfaced loudly at first use
    google_genai = None
    genai_errors = None
    genai_types = None


class ModelUnavailableForAllKeys(RuntimeError):
    """Every configured key rejected the requested model.

    Distinct from a transient failure: retrying cannot help, because the model
    is retired or not enabled for any key in the pool.
    """


class AllKeysExhausted(RuntimeError):
    """No key is currently usable and waiting will not help in time."""


# Substrings identifying "this API key cannot use this model" rather than
# "this key is broken". Google returns 404 for a model that is retired, not yet
# enabled for the project, or restricted to existing users — and that verdict
# is PER KEY: "no longer available to new users" means older keys in the pool
# may still succeed. Verified in production: 30 consecutive failures all came
# from key 20 of 21 while other keys were never tried. (P0-1 — preserve.)
_MODEL_UNAVAILABLE_MARKERS = (
    "404",
    "not found for api version",
    "no longer available",
    "is not supported for generatecontent",
)


class GeminiClientPool:
    """One immutable client per API key."""

    def __init__(self) -> None:
        self._clients: dict[str, Any] = {}
        self._lock = threading.Lock()

    def client_for(self, key: str) -> Any:
        """Return the client bound to `key`, building it once on first use."""
        if google_genai is None:
            raise RuntimeError(
                "google-genai is not installed — Gemini generation is unavailable."
            )
        client = self._clients.get(key)
        if client is not None:
            return client
        with self._lock:
            # Re-check inside the lock; another thread may have built it.
            client = self._clients.get(key)
            if client is None:
                client = google_genai.Client(api_key=key)
                self._clients[key] = client
        return client

    def warm(self) -> int:
        """Pre-build a client per configured key. Returns how many exist.

        Called at startup so the ~2.5 s construction cost is paid once, off the
        request path, rather than by whichever unlucky user hits a cold key.
        """
        rotator = get_key_rotator()
        for key in rotator.keys:
            try:
                self.client_for(key)
            except Exception as exc:  # pragma: no cover - never block startup
                logger.error(
                    "[gemini] could not build client for key %s: %s",
                    rotator.key_index(key), exc,
                )
        return len(self._clients)

    @property
    def built(self) -> int:
        return len(self._clients)


_pool = GeminiClientPool()


def get_client_pool() -> GeminiClientPool:
    return _pool


# ── failure classification ───────────────────────────────────────────────────

def _status_code(exc: Exception) -> Optional[int]:
    """HTTP status from a google-genai APIError, if it carries one."""
    for attr in ("code", "status_code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    status = getattr(exc, "status", None)
    if isinstance(status, int):
        return status
    return None


def classify_failure(exc: Exception) -> str:
    """One of: rate_limit | invalid_key | server_error | model_unavailable | fatal.

    Ordered so a STRUCTURED signal always beats a substring. S18 recorded the
    inverse mistake — `"503" in error_msg` matched a token count like "503
    tokens" and misclassified a capability gap as a transient server error —
    so status codes are consulted first and text only as a fallback.
    """
    code = _status_code(exc)
    if code == 429:
        return "rate_limit"
    if code in (401, 403):
        return "invalid_key"
    if code == 404:
        return "model_unavailable"
    if code is not None and 500 <= code < 600:
        return "server_error"

    text = str(exc).lower()
    if "resource_exhausted" in text or "quota" in text or "429" in text:
        return "rate_limit"
    if "api_key_invalid" in text or "permission_denied" in text or "403" in text:
        return "invalid_key"
    if any(marker in text for marker in _MODEL_UNAVAILABLE_MARKERS):
        return "model_unavailable"
    if "unavailable" in text or "internal error" in text or "503" in text or "500" in text:
        return "server_error"
    return "fatal"


_COOLDOWN_SECONDS = {
    "rate_limit": 300.0,   # daily/per-minute quota — long
    "server_error": 30.0,  # transient — short
}


async def _acquire_key(deadline: float) -> str:
    """A healthy key, waiting asynchronously if every key is cooling."""
    rotator = get_key_rotator()
    while True:
        key = rotator.try_get_key()
        if key is not None:
            return key

        wait = rotator.seconds_until_next_key()
        if wait is None:
            raise AllKeysExhausted(
                "Every configured Gemini API key is invalid (403). "
                "Add valid keys and restart."
            )
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0 or wait > remaining:
            raise AllKeysExhausted(
                f"All Gemini API keys are cooling down; the soonest becomes "
                f"available in {wait:.0f}s."
            )
        logger.warning("[gemini] all keys cooling — waiting %.1fs", wait)
        # asyncio.sleep, never time.sleep: this runs on the event loop.
        await asyncio.sleep(wait)


async def run_with_rotation(
    operation: Callable[[Any], Any],
    *,
    purpose: str = "generation",
    max_wait_seconds: float = 60.0,
) -> Any:
    """Run `operation(client)` on a healthy key, retrying on retryable failures.

    `operation` receives a client bound to the selected key and returns an
    awaitable. It must be safe to call more than once — a retry re-runs the
    ENTIRE request on a different key, per the request lifecycle.
    """
    rotator = get_key_rotator()
    pool = get_client_pool()
    total = max(1, len(rotator.keys))
    deadline = asyncio.get_running_loop().time() + max_wait_seconds

    keys_rejecting_model: set[str] = set()
    last_exc: Optional[Exception] = None

    for _ in range(total * 2):
        key = await _acquire_key(deadline)
        idx = rotator.key_index(key)
        try:
            return await operation(pool.client_for(key))
        except Exception as exc:  # noqa: BLE001 - classified immediately below
            last_exc = exc
            kind = classify_failure(exc)

            if kind == "rate_limit":
                logger.warning("[gemini] key %s rate-limited during %s", idx, purpose)
                rotator.report_rate_limit(key, int(_COOLDOWN_SECONDS["rate_limit"]))
            elif kind == "invalid_key":
                rotator.report_invalid_key(key)
            elif kind == "server_error":
                logger.warning("[gemini] transient server error on key %s", idx)
                rotator.report_rate_limit(key, int(_COOLDOWN_SECONDS["server_error"]))
            elif kind == "model_unavailable":
                # A capability gap, NOT a broken key. Cooling it here would
                # poison a healthy key for 300s over a per-key model
                # restriction — the exact mistake noted in the pitfalls list.
                keys_rejecting_model.add(key)
                logger.warning(
                    "[gemini] key %s cannot use this model (%d/%d keys rejected it): %s",
                    idx, len(keys_rejecting_model), total, str(exc)[:120],
                )
                if len(keys_rejecting_model) >= total:
                    raise ModelUnavailableForAllKeys(
                        f"No configured Gemini API key can access this model. "
                        f"Last error: {exc}"
                    ) from exc
            else:
                # Unrecoverable and not key-related: surface it unchanged
                # rather than burning the pool retrying something deterministic.
                logger.error("[gemini] unrecoverable error during %s: %s", purpose, exc)
                raise

    raise AllKeysExhausted(
        f"All Gemini API keys exhausted or on cooldown during {purpose}."
    ) from last_exc


async def stream_with_rotation(
    open_stream: Callable[[Any], Any],
    *,
    purpose: str = "streaming",
    max_wait_seconds: float = 60.0,
) -> AsyncGenerator[Any, None]:
    """Open a stream on a healthy key, then stay on that key for its duration.

    Rotation applies ONLY to establishing the stream. Once the first chunk has
    been delivered the key is fixed: switching mid-stream would restart
    generation on a different key and splice two different completions into one
    answer, which is worse than failing. This mirrors the required lifecycle —
    "if streaming has already begun, continue using the same key".
    """
    rotator = get_key_rotator()
    pool = get_client_pool()
    total = max(1, len(rotator.keys))
    deadline = asyncio.get_running_loop().time() + max_wait_seconds

    keys_rejecting_model: set[str] = set()
    last_exc: Optional[Exception] = None
    stream = None
    started = False

    for _ in range(total * 2):
        key = await _acquire_key(deadline)
        idx = rotator.key_index(key)
        try:
            stream = await open_stream(pool.client_for(key))
            started = True
            break
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            kind = classify_failure(exc)
            if kind == "rate_limit":
                logger.warning("[gemini] key %s rate-limited opening %s", idx, purpose)
                rotator.report_rate_limit(key, int(_COOLDOWN_SECONDS["rate_limit"]))
            elif kind == "invalid_key":
                rotator.report_invalid_key(key)
            elif kind == "server_error":
                rotator.report_rate_limit(key, int(_COOLDOWN_SECONDS["server_error"]))
            elif kind == "model_unavailable":
                keys_rejecting_model.add(key)
                if len(keys_rejecting_model) >= total:
                    raise ModelUnavailableForAllKeys(
                        f"No configured Gemini API key can access this model. "
                        f"Last error: {exc}"
                    ) from exc
            else:
                logger.error("[gemini] unrecoverable error opening %s: %s", purpose, exc)
                raise

    if not started:
        raise AllKeysExhausted(
            f"All Gemini API keys exhausted or on cooldown opening {purpose}."
        ) from last_exc

    # Past this point the key is committed. A mid-stream failure propagates.
    #
    # S1 (preserve): bound each STEP, not the whole stream. Total generation
    # time is legitimately long, but a chunk that never arrives previously hung
    # the request forever — `generate_stream` had no timeout at all while
    # `_provider_generate` enforced this same setting.
    from app.core.config import settings as _settings

    iterator = stream.__aiter__()
    while True:
        try:
            chunk = await asyncio.wait_for(
                iterator.__anext__(), timeout=_settings.LLM_TIMEOUT_SECONDS
            )
        except StopAsyncIteration:
            break
        except asyncio.TimeoutError:
            logger.error(
                "[gemini] stream stalled — no chunk within %ss. Ending the stream "
                "rather than hanging the request indefinitely.",
                _settings.LLM_TIMEOUT_SECONDS,
            )
            return
        yield chunk
