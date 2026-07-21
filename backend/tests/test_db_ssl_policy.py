"""Regression tests for DEBUG_MASTER_PLAN H-9 (newly discovered).

Both DB engines forced SSL unconditionally — sync via `sslmode=require`
appended to every DSN, async via connect_args {"ssl": "require"} — so the
application could not connect to ANY non-SSL Postgres, including the
project's own docker-compose stack. SSL is now forced only for non-local
hosts (same policy as alembic/env.py, H-8); explicit sslmode params are
always honored.
"""
from app.core.config import Settings, _is_local_db_host
from app.db.session import get_engine_args


def _settings(server: str) -> Settings:
    return Settings(
        AUTH_SECRET_KEY="x", CSRF_SECRET_KEY="x", FRONTEND_URL="http://x",
        POSTGRES_SERVER=server, POSTGRES_PORT="5432",
        POSTGRES_USER="u", POSTGRES_PASSWORD="p", POSTGRES_DB="d",
        DATABASE_URL=None,
        REDIS_URL="redis://localhost:6379/0",
        CELERY_BROKER_URL="redis://localhost:6379/0",
        CELERY_RESULT_BACKEND="redis://localhost:6379/0",
        _env_file=None,
    )


def test_local_hosts_get_no_forced_sslmode():
    for host in ("localhost", "127.0.0.1", "pgbouncer", "db"):
        assert "sslmode" not in _settings(host).sync_database_url, host


def test_remote_hosts_still_get_sslmode_require():
    url = _settings("aws-1.pooler.supabase.com").sync_database_url
    assert "sslmode=require" in url


def test_explicit_sslmode_is_preserved():
    s = _settings("localhost")
    s.DATABASE_URL = "postgresql://u:p@localhost:5432/d?sslmode=require"
    assert s.sync_database_url.count("sslmode=require") == 1


def test_async_engine_args_ssl_policy():
    _, local_args = get_engine_args("postgresql+asyncpg://u:p@localhost:5432/d", is_async=True)
    assert "ssl" not in local_args.get("connect_args", {})

    _, remote_args = get_engine_args(
        "postgresql+asyncpg://u:p@aws-1.pooler.supabase.com:5432/d", is_async=True
    )
    assert remote_args["connect_args"]["ssl"] == "require"


def test_helper_host_detection():
    assert _is_local_db_host("postgresql://u:p@localhost:5432/d")
    assert not _is_local_db_host("postgresql://u:p@example.com:5432/d")
