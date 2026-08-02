"""Regression guard for final_audit S12.

Six call sites did `try: import aioredis ... except Exception: return None`.
`aioredis` is NOT installed in this environment, and 2.0.1 is broken on Python
3.11 (this stack's pinned version) with "duplicate base class TimeoutError".
It has been deprecated in favour of `redis.asyncio` since 2022.

So every Redis path returned None — silently, with no log line — and these
advertised behaviours were inert:

  • DeviceFingerprintMiddleware's repeat-trial-registration block
  • the retrieval cache (every query paid full cost)
  • registration and feedback IP rate limits (fail-open)
  • the post-delete cache purge (deleted content could still be served)

The mechanism is the real defect: `except Exception: return None` makes a
MISSING DEPENDENCY indistinguishable from a cache miss. These tests pin that
the working library is used, that no module imports the dead one, and that an
unavailable client is reported LOUDLY rather than erased.
"""
import importlib
import logging
import pathlib

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[1]

REDIS_USING_MODULES = [
    "app.core.middleware",
    "app.core.redis_client",
    "app.api.v1.endpoints.auth",
    "app.api.v1.endpoints.feedback",
    "app.api.v1.endpoints.query",
    "app.api.v1.endpoints.documents",
]


def test_the_installed_async_redis_library_is_importable():
    """`redis.asyncio` must be present — it is what the code now depends on."""
    import redis.asyncio  # noqa: F401


def test_aioredis_is_not_imported_anywhere_in_the_app():
    """Importing a package that is not installed is not a fallback path.

    Matched over the parsed AST, not the source text: `redis_client.py`'s own
    docstring quotes the old `import aioredis` line while explaining why it was
    removed, and a text scan flags that explanation as a violation. The first
    version of this test did exactly that.
    """
    import ast

    offenders = []
    for path in (BACKEND / "app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(n.split(".")[0] == "aioredis" for n in names):
                offenders.append(f"{path.relative_to(BACKEND)}:{node.lineno}")
    assert not offenders, (
        f"aioredis is imported at {offenders}. It is not installed, and 2.0.1 "
        "is broken on Python 3.11 — the import raises and a bare except turns "
        "that into a silent no-op (S12). Use app.core.redis_client.get_redis."
    )


def test_aioredis_is_not_a_declared_dependency():
    for req in ("requirements.txt", "requirements-deploy.txt"):
        for line in (BACKEND / req).read_text(encoding="utf-8").splitlines():
            assert not line.strip().startswith("aioredis"), (
                f"{req} still declares aioredis — a dependency the code no "
                "longer uses and that cannot install cleanly on Python 3.11."
            )


@pytest.mark.asyncio
async def test_unavailable_redis_is_logged_at_error_not_swallowed(caplog, monkeypatch):
    """A missing client must be distinguishable from a cache miss.

    Driven with a genuinely unparseable REDIS_URL rather than a patched module,
    so the real `redis.asyncio.from_url` raises for a real reason.
    """
    import app.core.redis_client as redis_client

    importlib.reload(redis_client)  # reset the once-per-process latch
    monkeypatch.setattr(
        redis_client.settings, "REDIS_URL", "not-a-valid-scheme://x", raising=False
    )

    with caplog.at_level(logging.ERROR, logger="app.core.redis_client"):
        client = await redis_client.get_redis()

    assert client is None, "callers rely on None to degrade gracefully"
    assert any("[redis]" in r.message for r in caplog.records), (
        "an unavailable Redis client produced NO error log. That is what made "
        "a missing dependency look like a cache miss for the entire life of "
        "this feature (S12)."
    )


@pytest.mark.asyncio
async def test_the_error_is_logged_once_per_process_not_per_request(caplog, monkeypatch):
    """Loud, but not a flood — this sits on the request path."""
    import app.core.redis_client as redis_client

    importlib.reload(redis_client)
    monkeypatch.setattr(
        redis_client.settings, "REDIS_URL", "not-a-valid-scheme://x", raising=False
    )

    with caplog.at_level(logging.ERROR, logger="app.core.redis_client"):
        for _ in range(5):
            await redis_client.get_redis()

    hits = [r for r in caplog.records if "[redis]" in r.message]
    assert len(hits) == 1, (
        f"logged {len(hits)} times for 5 calls; a Redis outage would flood the "
        "log from the request path. Expected exactly one per process."
    )
