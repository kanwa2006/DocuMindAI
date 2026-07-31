"""Regression tests for P0-5 (Supabase Supavisor session-mode pool exhaustion).

The API's async engine was hardcoded to pool_size=10 / max_overflow=20 — a
30-connection ceiling — while Supabase's Supavisor pooler in SESSION mode caps
the entire project at 15. SQLAlchemy retains pooled connections after use, so
this did not merely spike under load: measured at rest, with worker and beat
stopped, the API held all 15 (14 idle, 1 active). Nothing else could connect.
The Celery worker could not drain its queue and the /health probe could not
open its 16th connection, so the backend container sat "unhealthy" for 19h.

The sync engine had the same defect less visibly: it passed no pool arguments
at all, so it silently took SQLAlchemy's defaults (5 + 10 = 15 per process) —
one worker child could consume the whole budget, and Celery's prefork default
of os.cpu_count() children could ask for 8x that.

These tests pin the wiring so a revert fails CI instead of silently
re-exhausting the pooler. They deliberately do NOT assert specific numbers —
the budget is tuned per deployment tier via env — only that the configured
values actually reach the engines.
"""
import re
from pathlib import Path

from app.core.config import settings
from app.db.session import engine, sync_engine

COMPOSE = Path(__file__).resolve().parents[2] / "infrastructure" / "docker-compose.yml"


def test_async_engine_pool_matches_settings():
    """The API pool must come from settings, not a hardcoded literal.

    Guards the exact regression: a hardcoded 10/20 that no longer tracks the
    deployment's pooler ceiling.
    """
    assert engine.pool.size() == settings.DB_POOL_SIZE
    assert engine.pool._max_overflow == settings.DB_MAX_OVERFLOW


def test_sync_engine_pool_is_explicit():
    """The Celery/sync engine must not fall back to SQLAlchemy's 5+10 default.

    This is per-process and multiplied by worker concurrency, so an implicit
    default here is what let a single child consume the entire budget.
    """
    assert sync_engine.pool.size() == settings.WORKER_DB_POOL_SIZE
    assert sync_engine.pool._max_overflow == settings.WORKER_DB_MAX_OVERFLOW


def test_total_budget_fits_session_mode_ceiling():
    """Defaults must fit under Supavisor session mode's 15-connection cap.

    API + (2 worker children) + beat + the unpooled /health ping. If someone
    raises a default without moving to transaction mode, this fails loudly
    rather than in production.
    """
    api = settings.DB_POOL_SIZE + settings.DB_MAX_OVERFLOW
    per_child = settings.WORKER_DB_POOL_SIZE + settings.WORKER_DB_MAX_OVERFLOW
    total = api + (2 * per_child) + per_child + 1  # api + workers + beat + health
    assert total <= 15, (
        f"Default connection budget is {total}, over Supabase session mode's 15. "
        "Either lower the defaults or move the deployment to transaction mode."
    )


def test_worker_process_init_disposes_inherited_pool_with_close_false():
    """Fork safety: prefork children must abandon, not close, inherited sockets.

    `sync_engine` is built at import time in the Celery parent and inherited
    across fork(). close=True would close file descriptors the parent still
    believes it owns; only close=False is safe here. A test that merely
    asserted "dispose was called" would pass even if the flag flipped back to
    the dangerous default, so this asserts the argument specifically.
    """
    import app.workers.celery_app as celery_module

    calls = {}

    def fake_dispose(close=True):
        calls["close"] = close

    original = sync_engine.dispose
    sync_engine.dispose = fake_dispose
    try:
        celery_module._dispose_inherited_db_pool()
    finally:
        sync_engine.dispose = original

    assert calls, "worker_process_init handler never disposed the inherited pool"
    assert calls["close"] is False, (
        "dispose() must be called with close=False; close=True severs sockets "
        "still shared with the Celery parent process"
    )


def test_compose_worker_concurrency_is_pinned():
    """Celery's prefork default is os.cpu_count(), which makes the worker's
    share of the connection budget vary by host — unsizable at deploy time.
    """
    text = COMPOSE.read_text(encoding="utf-8")
    worker_cmd = [
        ln for ln in text.splitlines()
        if "celery" in ln and "worker" in ln and ln.strip().startswith("command:")
    ]
    assert worker_cmd, "no worker command found in docker-compose.yml"
    assert re.search(r"--concurrency=\d+", worker_cmd[0]), (
        "worker command must pin --concurrency; without it Celery defaults to "
        "os.cpu_count() and the DB connection budget changes with the host"
    )
