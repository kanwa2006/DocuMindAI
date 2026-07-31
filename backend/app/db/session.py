from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


def _is_supavisor_pooler(url: str) -> bool:
    """
    True for Supabase Supavisor pooler hosts. Both session (:5432) and
    transaction (:6543) modes go through Supavisor; transaction mode in
    particular breaks asyncpg's prepared-statement cache, so we disable it.
    Detecting by host string keeps this safe for direct-connect setups.
    """
    return "pooler.supabase.com" in (url or "")


def get_engine_args(url: str, is_async: bool):
    args = {}
    if "sqlite" in url:
        args["connect_args"] = {"check_same_thread": False}
        if is_async:
            url = url.replace("sqlite://", "sqlite+aiosqlite://")
    elif "postgresql" in url or "postgres" in url:
        # Supabase (and most managed PG) requires SSL.
        # asyncpg accepts the `ssl` kwarg; psycopg2 rejects it (must be `sslmode`).
        # For sync, sslmode is already baked into the URL by settings.sync_database_url,
        # so no connect_args needed here.
        # H-9: never force SSL for local/compose hosts — the old unconditional
        # {"ssl": "require"} made the async engine unable to connect to any
        # non-SSL Postgres (including the project's own docker-compose db).
        from app.core.config import _is_local_db_host
        if is_async and not _is_local_db_host(url):
            connect_args = {"ssl": "require"}
            # When going through Supavisor (either pooler port), disable the
            # asyncpg prepared-statement cache. In transaction mode the pooler
            # rebinds backends between statements and a cached plan can blow
            # up with "prepared statement does not exist". Session mode tolerates
            # it but a zero cache is harmless there.
            if _is_supavisor_pooler(url):
                connect_args["statement_cache_size"] = 0
                connect_args["prepared_statement_cache_size"] = 0
            args["connect_args"] = connect_args
    return url, args


async_url, async_args = get_engine_args(settings.async_database_url, is_async=True)

# P0-5: the connection budget is sized in core/config.py, NOT here, because it
# has to be tunable per deployment tier — it must fit under the ceiling of
# whatever pooler is in front of Postgres. See the comment on DB_POOL_SIZE.
#
# The previous hardcoded pool_size=10/max_overflow=20 allowed the API alone to
# open 30 connections against Supabase session mode's project-wide cap of 15.
# SQLAlchemy retains pooled connections after use, so this did not merely spike
# under load — it held the ceiling permanently. Measured with worker and beat
# stopped: 14 idle + 1 active = 15/15 consumed by the API at rest.
_is_sqlite = "sqlite" in async_url
engine = create_async_engine(
    async_url,
    echo=False,
    future=True,
    # SQLite doesn't support pool parameters
    **({} if _is_sqlite else {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        # Essential in front of a pooler: Supavisor can drop a server-side
        # connection under us, and a stale pooled connection would otherwise
        # surface as a request-time error rather than a transparent reconnect.
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    }),
    **async_args,
)


AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# Sync Engine for Celery Workers
#
# P0-5: this engine is created at IMPORT time, in the Celery parent process,
# and every prefork child inherits it across fork(). Two consequences:
#
#   1. Sizing is PER CHILD, so the effective ceiling is
#      concurrency x (pool_size + max_overflow). SQLAlchemy's unstated default
#      is 5+10=15, which meant a single worker child could consume the entire
#      15-connection session-mode budget, and eight of them could ask for 120.
#   2. Inherited pooled connections are shared TCP sockets. Two processes
#      writing to one socket corrupts the protocol stream. app/workers/
#      celery_app.py disposes the inherited pool in worker_process_init; see
#      the comment there for why it must use close=False.
sync_url, sync_args = get_engine_args(settings.sync_database_url, is_async=False)
# SQLite is a supported URL here (see get_engine_args above and
# retrieval_service.py) and its pool implementation rejects pool_size /
# max_overflow, so apply the budget only on real pooled backends.
_sync_is_sqlite = "sqlite" in sync_url
sync_engine = create_engine(
    sync_url,
    pool_pre_ping=True,
    **({} if _sync_is_sqlite else {
        "pool_size": settings.WORKER_DB_POOL_SIZE,
        "max_overflow": settings.WORKER_DB_MAX_OVERFLOW,
        "pool_recycle": 3600,
    }),
    **sync_args,
)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
