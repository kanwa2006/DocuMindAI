import asyncio
import os
import sys
from logging.config import fileConfig

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.core.config import settings
from app.db.base import Base
import app.models  # Ensures models are registered for autogenerate

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = settings.sync_database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})

    # Normalise the URL — ensure asyncpg driver prefix is present
    raw_url = str(settings.async_database_url)
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw_url.startswith("postgresql://") and "+asyncpg" not in raw_url:
        raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    configuration["sqlalchemy.url"] = raw_url

    # H-8: SSL was hardcoded to "require" for every Postgres URL, which made
    # migrations fail against any non-SSL server (the CI pgvector service
    # container, local docker, scratch DBs) with "rejected SSL upgrade".
    # Honor an explicit ssl/sslmode URL param first (stripped from the URL —
    # the asyncpg dialect rejects sslmode as a connect kwarg), otherwise
    # require SSL only for non-local hosts (Supabase et al.).
    from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit

    split = urlsplit(raw_url)
    ssl_override = None
    kept_params = []
    for key, value in parse_qsl(split.query):
        if key.lower() in ("ssl", "sslmode"):
            ssl_override = value.lower()
        else:
            kept_params.append((key, value))
    raw_url = urlunsplit(
        (split.scheme, split.netloc, split.path, urlencode(kept_params), split.fragment)
    )
    configuration["sqlalchemy.url"] = raw_url

    _LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "db", "pgbouncer", "postgres"}
    connect_args: dict = {}
    if ssl_override is not None:
        if ssl_override not in ("disable", "allow", "false", "off"):
            connect_args["ssl"] = "require"
    elif (split.hostname or "").lower() not in _LOCAL_HOSTS:
        connect_args["ssl"] = "require"

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
