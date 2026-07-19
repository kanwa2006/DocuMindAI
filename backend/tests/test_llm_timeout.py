"""Regression tests for DEBUG_MASTER_PLAN L-11.

Non-streaming LLM calls had no server-side cap — a slow upstream pinned a
worker thread until the client gave up. Every LLMService generation path
now runs under asyncio.wait_for(settings.LLM_TIMEOUT_SECONDS).
"""
import asyncio

import pytest

from app.services.llm_service import LLMService, DummyLLMProvider


class SlowProvider(DummyLLMProvider):
    async def generate(self, system_prompt, user_prompt):
        await asyncio.sleep(5)
        return "too late"


@pytest.mark.asyncio
async def test_generate_times_out(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LLM_TIMEOUT_SECONDS", 0.05)
    service = LLMService(provider=SlowProvider())
    with pytest.raises(asyncio.TimeoutError):
        await service.generate("sys", "user")


@pytest.mark.asyncio
async def test_generate_answer_times_out(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LLM_TIMEOUT_SECONDS", 0.05)
    service = LLMService(provider=SlowProvider())
    with pytest.raises(asyncio.TimeoutError):
        await service.generate_answer("q", "some grounded context")


@pytest.mark.asyncio
async def test_fast_calls_unaffected():
    service = LLMService(provider=DummyLLMProvider())
    result = await service.generate("sys", "user")
    assert result  # normal path returns within the default cap
