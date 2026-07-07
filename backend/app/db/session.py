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
        if is_async:
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

# FIX 6.5: Connection pool tuning — prevents exhaustion under concurrent SSE loads
_is_sqlite = "sqlite" in async_url
engine = create_async_engine(
    async_url,
    echo=False,
    future=True,
    # SQLite doesn't support pool parameters
    **({} if _is_sqlite else {
        "pool_size": 10,
        "max_overflow": 20,
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
sync_url, sync_args = get_engine_args(settings.sync_database_url, is_async=False)
sync_engine = create_engine(sync_url, pool_pre_ping=True, **sync_args)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
