from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

import psycopg2
from urllib.parse import urlparse, unquote
import asyncio
import redis.asyncio as redis

from app.core.config import settings
from app.services.llm_key_rotation import get_key_rotator
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def _db_ping():
    """Direct psycopg2 ping — uses sslmode (not ssl) which psycopg2 requires."""
    from app.core.config import _is_local_db_host

    u = urlparse(settings.sync_database_url)

    # urlparse() does NOT percent-decode userinfo, but psycopg2's keyword
    # arguments expect the literal credential. A password containing any
    # character that must be encoded in a URL — '@' as %40 is the common case,
    # and Supabase-generated passwords frequently contain one — was therefore
    # sent verbatim ("Kanwams%4012345" instead of "Kanwams@12345") and rejected.
    #
    # This was not a harmless false alarm: the healthcheck re-runs every 10s, so
    # each failure became another rejected login against the upstream. Supabase's
    # Supavisor pooler tripped its circuit breaker after ~210 attempts
    # (ECIRCUITBREAKER) and began refusing *all* new connections, including the
    # correctly-authenticated ones used by the application itself.
    #
    # SQLAlchemy decodes this for us on the async engine path; only this direct
    # psycopg2 call needed it.
    conn = psycopg2.connect(
        host=u.hostname,
        port=u.port or 5432,
        dbname=u.path.lstrip("/"),
        user=unquote(u.username or ""),
        password=unquote(u.password or ""),
        # H-9: forcing require here broke health against non-SSL local/compose
        # Postgres; prefer negotiates SSL when the server offers it.
        sslmode="prefer" if _is_local_db_host(settings.sync_database_url) else "require",
        connect_timeout=5,
    )

    conn.close()


@router.get("/health")
async def health_check():
    status = {
        "api": "ok",
        "db": "unknown",
        "redis": "unknown",
    }

    # Check DB
    try:
        await asyncio.to_thread(_db_ping)
        status["db"] = "ok"
    except Exception as e:
        # L-12: never echo raw exceptions (can leak DSN/host); log server-side.
        logger.error(f"[health] DB check failed: {e}")
        status["db"] = "error"

    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        # close() in a finally: a failing ping() (the exact case this endpoint
        # exists to detect) would otherwise skip it. Health is polled
        # continuously, so a Redis outage leaked a connection per probe.
        try:
            await r.ping()
            status["redis"] = "ok"
        finally:
            await r.close()
    except Exception as e:
        logger.error(f"[health] Redis check failed: {e}")
        status["redis"] = "error"

    if status["db"] != "ok" or status["redis"] != "ok":
        raise HTTPException(
            status_code=503,
            detail=status,
        )

    return status


@router.get("/health/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
):
    status = {
        "api": "ok",
        "db": "unknown",
        "redis": "unknown",
        "api_keys": {},
        # S8: which embedding model THIS process is using. The API container
        # and the Celery worker load models independently; if they disagree,
        # document vectors and query vectors are not comparable and their
        # similarity is plausible garbage rather than an obvious error.
        # Compare this value across processes when retrieval is inexplicably
        # bad. Cheap and never raises — a diagnostic must not break /health.
        "embedding": "unknown",
    }

    try:
        from app.services.embedding_service import embedding_service
        status["embedding"] = embedding_service.signature
    except Exception as e:
        logger.error(f"[health] Embedding signature unavailable: {e}")
        status["embedding"] = "error"

    try:
        await asyncio.to_thread(_db_ping)
        status["db"] = "ok"
    except Exception as e:
        # L-12: never echo raw exceptions (can leak DSN/host); log server-side.
        logger.error(f"[health] DB check failed: {e}")
        status["db"] = "error"

    try:
        r = redis.from_url(settings.REDIS_URL)
        # close() in a finally: a failing ping() (the exact case this endpoint
        # exists to detect) would otherwise skip it. Health is polled
        # continuously, so a Redis outage leaked a connection per probe.
        try:
            await r.ping()
            status["redis"] = "ok"
        finally:
            await r.close()
    except Exception as e:
        logger.error(f"[health] Redis check failed: {e}")
        status["redis"] = "error"

    try:
        ks = get_key_rotator().key_status

        status["api_keys"] = {
            "total": ks["total"],
            "available": ks["available"],
            "exhausted": ks["cooling"],
            "invalid": ks["invalid"],
        }

    except Exception as e:
        logger.error(f"[health] Key-status check failed: {e}")
        status["api_keys"] = {"error": "unavailable"}

    if status["db"] != "ok" or status["redis"] != "ok":
        raise HTTPException(
            status_code=503,
            detail=status,
        )

    return status