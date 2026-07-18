"""Regression tests for DEBUG_MASTER_PLAN C-6 (newly discovered).

`llm_service.generate(system_prompt, user_prompt)` was called from 10
sites (legal, finance, research, reports, deep-research) but only the
*provider* defined `generate`; the service raised AttributeError. Pins the
service-level method and its delegation to the provider.
"""
import pytest

from app.services.llm_service import LLMService, DummyLLMProvider, llm_service


def test_generate_exists_on_service():
    assert hasattr(LLMService, "generate")
    assert callable(getattr(llm_service, "generate", None))


@pytest.mark.asyncio
async def test_generate_delegates_to_provider():
    class RecordingProvider(DummyLLMProvider):
        def __init__(self):
            self.calls = []

        async def generate(self, system_prompt, user_prompt):
            self.calls.append((system_prompt, user_prompt))
            return "provider says hi"

    provider = RecordingProvider()
    service = LLMService(provider=provider)
    result = await service.generate("sys", "user")
    assert result == "provider says hi"
    assert provider.calls == [("sys", "user")]
