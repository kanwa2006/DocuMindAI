"""Single async Redis client factory.

S12 — six call sites each did:

    try:
        import aioredis
        return await aioredis.from_url(settings.REDIS_URL, ...)
    except Exception:
        return None

`aioredis` is **not installed** in this environment, and `aioredis` 2.0.1 is
known-broken on Python 3.11 (this stack's pinned version) with
`TypeError: duplicate base class TimeoutError`. The package has been
deprecated in favour of `redis.asyncio` since 2022. So every one of those
calls raised `ModuleNotFoundError`, was swallowed by the bare `except`, and
returned `None` — with **no log line anywhere**.

What that silently disabled:

  • `DeviceFingerprintMiddleware` — an advertised abuse control that stops
    repeat trial registrations. Inert, with zero evidence in the logs.
  • the retrieval cache — every query paid full retrieval cost while the code
    presented a working cache path
  • registration and feedback IP rate limits — fail-open

The mechanism is the point: `except Exception: return None` makes a MISSING
DEPENDENCY indistinguishable from a cache miss. Both look like "no Redis
today". That is precisely the silent-fallback pattern CLAUDE.md's
loud-degradation invariant forbids.

So this module does two things the old code did not: it uses the library that
is actually installed, and when a client genuinely cannot be constructed it
says so at ERROR — once per process, so a Redis outage does not flood the log
on every request.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Log the failure once per process, not once per request.
_unavailable_logged = False


async def get_redis() -> Optional[Any]:
    """Return a connected `redis.asyncio` client, or None with a LOUD error.

    Callers keep treating `None` as "Redis unavailable, degrade gracefully" —
    that behaviour is deliberate for a cache and for best-effort rate limits.
    What changes is that the reason is now visible instead of being erased.
    """
    global _unavailable_logged
    try:
        import redis.asyncio as redis_asyncio

        return redis_asyncio.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
    except Exception as exc:  # noqa: BLE001 - must never break a request path
        if not _unavailable_logged:
            _unavailable_logged = True
            logger.error(
                "[redis] client could not be constructed (%s: %s). Trial abuse "
                "prevention, the retrieval cache and IP rate limits are all "
                "DEGRADED until this is fixed. Logged once per process.",
                type(exc).__name__,
                exc,
            )
        return None
