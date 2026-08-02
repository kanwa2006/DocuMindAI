"""Regression guard for final_audit P-3.

`DummyLLMProvider.generate` simulated latency with `time.sleep(0.5)` inside an
`async def`. That blocks the entire event loop, not just the caller: every
concurrent request on the worker stalls for the full 500 ms.

DummyLLMProvider only serves when no Gemini key is configured, so this is not
on a correctly-configured production path — but it turns an already-degraded
deployment into a fully serialized one, which is the worst possible moment to
lose concurrency.

The test measures the property rather than the source text: N concurrent calls
must overlap. With a blocking sleep they serialize to N x 0.5 s; with
`await asyncio.sleep` they all finish in roughly 0.5 s.
"""
import asyncio
import time

import pytest

from app.services.llm_service import DummyLLMProvider

CALLS = 4
SLEEP_PER_CALL = 0.5


@pytest.mark.asyncio
async def test_concurrent_dummy_generations_overlap():
    provider = DummyLLMProvider()

    start = time.perf_counter()
    await asyncio.gather(
        *(provider.generate("system", f"prompt {i}") for i in range(CALLS))
    )
    elapsed = time.perf_counter() - start

    serialized = CALLS * SLEEP_PER_CALL  # 2.0s if the loop is blocked
    # Generous ceiling: real concurrency lands near 0.5s. Anything at or above
    # ~1.2s means the calls are not overlapping.
    ceiling = SLEEP_PER_CALL + 0.7

    assert elapsed < ceiling, (
        f"{CALLS} concurrent DummyLLMProvider.generate calls took {elapsed:.2f}s "
        f"(ceiling {ceiling:.2f}s, fully serialized would be {serialized:.2f}s). "
        "A blocking time.sleep inside an async def stalls the whole event loop, "
        "so every other in-flight request waits too (P-3)."
    )
