"""Regression guard for final_audit S1, retargeted after the S5 migration.

**S1 (original):** `generate_stream` consumed the Gemini stream with a
synchronous `for chunk in stream_response:` inside an `async def`. Only the
call that OBTAINED the stream was wrapped in `run_in_executor`; the iteration
that performed the network I/O ran on the event loop thread, so one streaming
user froze the whole worker.

**Why this file changed:** S5 replaced `google.generativeai` with
`google.genai`, whose `client.aio.*` API is natively async. There is no longer
a blocking iterator to pump through an executor — the structure that caused S1
is gone rather than fixed in place.

That makes it more important, not less, that this guard tests the PROPERTY
(consuming a stream leaves the event loop free) rather than the old mechanism
(an executor pump). A future edit that reintroduces a synchronous `for` over a
blocking iterator would recreate S1 exactly, and this file must fail if it
does.

The previous version of this test patched `provider._execute_with_rotation`,
which no longer exists. With `raising=False` that patch silently did nothing
and the test began issuing REAL network calls — passing for the wrong reason
until the assertions happened to disagree with a live Gemini reply. Tests are
patched against the pool now, which is the seam the production code actually
uses.
"""
import asyncio
import time

import pytest

from app.core.config import settings
from app.services import gemini_client
from app.services.llm_service import GeminiLLMProvider

CHUNK_DELAY = 0.15
N_CHUNKS = 4


class _Chunk:
    def __init__(self, text):
        self.text = text
        self.candidates = []


class _AsyncStream:
    """An async stream whose chunks arrive slowly, WITHOUT blocking the loop."""

    def __init__(self, n, delay, stall_at=None):
        self._n, self._delay, self._stall_at, self._i = n, delay, stall_at, 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._stall_at is not None and self._i == self._stall_at:
            await asyncio.sleep(30)  # never arrives within the patched timeout
        if self._i >= self._n:
            raise StopAsyncIteration
        self._i += 1
        await asyncio.sleep(self._delay)
        return _Chunk(f"tok{self._i} ")


class _FakeModels:
    def __init__(self, stream_factory):
        self._stream_factory = stream_factory

    async def generate_content_stream(self, **kwargs):
        return self._stream_factory()


class _FakeClient:
    def __init__(self, stream_factory):
        self.aio = type("aio", (), {"models": _FakeModels(stream_factory)})()


@pytest.fixture
def fake_pool(monkeypatch):
    """Patch the client pool — the seam production code actually uses."""

    def _install(stream_factory):
        class _Pool:
            def client_for(self, key):
                return _FakeClient(stream_factory)

        monkeypatch.setattr(gemini_client, "get_client_pool", lambda: _Pool())
        return _Pool()

    return _install


@pytest.mark.asyncio
async def test_stream_consumption_leaves_the_event_loop_free(fake_pool):
    fake_pool(lambda: _AsyncStream(N_CHUNKS, CHUNK_DELAY))
    provider = GeminiLLMProvider()

    heartbeats = 0
    stop = False

    async def heartbeat():
        nonlocal heartbeats
        while not stop:
            heartbeats += 1
            await asyncio.sleep(0.01)

    hb = asyncio.create_task(heartbeat())
    tokens = [t async for t in provider.generate_stream("sys", "user")]
    stop = True
    await hb

    assert len(tokens) == N_CHUNKS, f"expected {N_CHUNKS} tokens, got {tokens}"

    total_blocked = N_CHUNKS * CHUNK_DELAY
    expected_ticks = total_blocked / 0.01
    assert heartbeats > expected_ticks * 0.3, (
        f"only {heartbeats} heartbeats while consuming a stream that takes "
        f"{total_blocked:.2f}s. The event loop was starved, which means stream "
        "iteration is blocking the loop thread again (S1)."
    )


@pytest.mark.asyncio
async def test_a_stalled_chunk_does_not_hang_forever(fake_pool, monkeypatch):
    """S1's second half: generate_stream had NO timeout at all."""
    monkeypatch.setattr(settings, "LLM_TIMEOUT_SECONDS", 1, raising=False)
    fake_pool(lambda: _AsyncStream(N_CHUNKS, 0.01, stall_at=2))
    provider = GeminiLLMProvider()

    started = time.perf_counter()
    tokens = [t async for t in provider.generate_stream("sys", "user")]
    elapsed = time.perf_counter() - started

    assert elapsed < 10, (
        f"a stalled stream took {elapsed:.1f}s to give up. Each chunk must be "
        "bounded by LLM_TIMEOUT_SECONDS, or a hung upstream holds the request "
        "open indefinitely (S1)."
    )
    assert len(tokens) == 2, f"expected the 2 pre-stall tokens, got {tokens}"


def test_stream_iteration_is_not_synchronous():
    """Structural backstop: a sync `for` over the stream would recreate S1."""
    import ast
    import inspect
    import textwrap

    src = textwrap.dedent(inspect.getsource(gemini_client.stream_with_rotation))
    tree = ast.parse(src)

    # Only a sync `for` OVER THE STREAM matters. `for _ in range(...)` is the
    # retry loop and is correct — the first version of this check flagged it.
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):  # ast.AsyncFor is a distinct node
            continue
        target = node.iter
        name = (
            target.id if isinstance(target, ast.Name)
            else getattr(target, "attr", None)
        )
        if name in {"stream", "iterator", "response", "stream_response"}:
            raise AssertionError(
                f"stream_with_rotation iterates `{name}` with a SYNCHRONOUS "
                "`for`. If that iterator does network I/O it blocks the event "
                "loop for every other request — this is S1 exactly."
            )
