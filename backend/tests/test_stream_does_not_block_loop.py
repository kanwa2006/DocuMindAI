"""Regression guard for final_audit S1.

`GeminiLLMProvider.generate_stream` consumed the Gemini stream with a
synchronous `for chunk in stream_response:` inside an `async def`. Only the
call that OBTAINED the stream was wrapped in `run_in_executor`; the iteration
that performs the network I/O was left on the event loop thread.

The returned object is a blocking generator whose `__next__` waits on the
network, so every chunk froze the entire worker — other requests, other SSE
streams, and the health check with them. This would be misdiagnosed as "Gemini
is slow" because the symptom appears everywhere except the code responsible.

The test measures the property: while a stream whose chunks each block for
BLOCK_S is being consumed, an independent coroutine must continue to make
progress on the loop. If iteration blocks the loop, that heartbeat starves.

Second test: a chunk that never arrives must not hang forever — generate_stream
had no timeout at all, while `_provider_generate` enforces
`LLM_TIMEOUT_SECONDS`.
"""
import asyncio
import time

import pytest

from app.core.config import settings
from app.services import llm_service as llm_module
from app.services.llm_service import GeminiLLMProvider

BLOCK_S = 0.15
N_CHUNKS = 4


class _Chunk:
    """Minimal stand-in for a Gemini stream chunk."""

    def __init__(self, text):
        self.text = text
        self.candidates = []


class _BlockingStream:
    """A sync generator whose every step blocks the calling thread."""

    def __init__(self, n, block_s, stall_forever_at=None):
        self._n = n
        self._block_s = block_s
        self._stall_at = stall_forever_at
        self._i = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._stall_at is not None and self._i == self._stall_at:
            time.sleep(30)  # never arrives within the test's patched timeout
        if self._i >= self._n:
            raise StopIteration
        self._i += 1
        time.sleep(self._block_s)
        return _Chunk(f"tok{self._i} ")


def _provider_with_stream(monkeypatch, stream):
    provider = GeminiLLMProvider.__new__(GeminiLLMProvider)

    async def _fake_execute(run):
        return stream

    monkeypatch.setattr(provider, "_execute_with_rotation", _fake_execute, raising=False)
    monkeypatch.setattr(llm_module, "genai", object(), raising=False)
    return provider


@pytest.mark.asyncio
async def test_stream_iteration_leaves_the_event_loop_free(monkeypatch):
    provider = _provider_with_stream(
        monkeypatch, _BlockingStream(N_CHUNKS, BLOCK_S)
    )

    heartbeats = 0
    stop = False

    async def heartbeat():
        nonlocal heartbeats
        while not stop:
            heartbeats += 1
            await asyncio.sleep(0.01)

    hb_task = asyncio.create_task(heartbeat())
    tokens = [t async for t in provider.generate_stream("sys", "user")]
    stop = True
    await hb_task

    assert len(tokens) == N_CHUNKS, f"expected {N_CHUNKS} tokens, got {tokens}"

    # Blocking iteration pins the loop for N_CHUNKS * BLOCK_S with the
    # heartbeat unable to run; a properly offloaded pump lets it tick freely.
    total_blocked = N_CHUNKS * BLOCK_S
    expected_ticks = total_blocked / 0.01
    assert heartbeats > expected_ticks * 0.3, (
        f"only {heartbeats} heartbeats while consuming a stream that blocks "
        f"{total_blocked:.2f}s in total. The event loop was starved, which "
        "means stream iteration is running on the loop thread instead of in an "
        "executor (S1)."
    )


@pytest.mark.asyncio
async def test_a_stalled_chunk_does_not_hang_forever(monkeypatch):
    monkeypatch.setattr(settings, "LLM_TIMEOUT_SECONDS", 1, raising=False)
    provider = _provider_with_stream(
        monkeypatch, _BlockingStream(N_CHUNKS, 0.01, stall_forever_at=2)
    )

    started = time.perf_counter()
    tokens = [t async for t in provider.generate_stream("sys", "user")]
    elapsed = time.perf_counter() - started

    assert elapsed < 10, (
        f"a stalled stream took {elapsed:.1f}s to give up. generate_stream must "
        "bound each chunk by LLM_TIMEOUT_SECONDS, or a hung upstream holds the "
        "request open indefinitely (S1)."
    )
    # It should still have yielded whatever arrived before the stall.
    assert len(tokens) == 2, f"expected the 2 pre-stall tokens, got {tokens}"
