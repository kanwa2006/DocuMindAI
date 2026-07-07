from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

import psycopg2
from urllib.parse import urlparse
import asyncio
import redis.asyncio as redis

from app.core.config import settings
from app.services.llm_key_rotation import get_key_rotator

router = APIRouter()


def _db_ping():
    """Direct psycopg2 ping — uses sslmode (not ssl) which psycopg2 requires."""
    u = urlparse(settings.sync_database_url)

    conn = psycopg2.connect(
        host=u.hostname,
        port=u.port or 5432,
        dbname=u.path.lstrip("/"),
        user=u.username,
        password=u.password or "",
        sslmode="require",
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
        status["db"] = f"error: {str(e)}"

    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        status["redis"] = "ok"
        await r.close()
    except Exception as e:
        status["redis"] = f"error: {str(e)}"

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
    }

    try:
        await asyncio.to_thread(_db_ping)
        status["db"] = "ok"
    except Exception as e:
        status["db"] = f"error: {str(e)}"

    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        status["redis"] = "ok"
        await r.close()
    except Exception as e:
        status["redis"] = f"error: {str(e)}"

    try:
        ks = get_key_rotator().key_status

        status["api_keys"] = {
            "total": ks["total"],
            "available": ks["available"],
            "exhausted": ks["cooling"],
            "invalid": ks["invalid"],
        }

    except Exception as e:
        status["api_keys"] = {
            "error": str(e)
        }

    if status["db"] != "ok" or status["redis"] != "ok":
        raise HTTPException(
            status_code=503,
            detail=status,
        )

    return status