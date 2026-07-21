"""Regression tests for DEBUG_MASTER_PLAN H-7.

`llm_service = LLMService()` used to construct the Gemini provider at
import time and raise RuntimeError without keys (ENVIRONMENT != test),
coupling every importing module to key availability. The provider is now
built lazily on first `.provider` access; the fail-loud guarantee moves to
first use with the same explicit error.
"""
from unittest.mock import patch

import pytest

from app.services import llm_service as llm_module
from app.services.llm_service import LLMService, DummyLLMProvider


def test_construction_never_builds_provider():
    with patch.object(LLMService, "_build_provider", side_effect=AssertionError("must be lazy")):
        service = LLMService()  # must not raise
    assert service._provider is None


def test_first_provider_access_fails_loud_without_keys(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    with patch.object(llm_module, "GeminiLLMProvider", side_effect=ValueError("No Gemini keys found")):
        service = LLMService()  # import-time equivalent: safe
        with pytest.raises(RuntimeError, match="Refusing to serve mock"):
            _ = service.provider  # first use: loud


def test_injected_provider_is_honored_without_building():
    provider = DummyLLMProvider()
    with patch.object(LLMService, "_build_provider", side_effect=AssertionError("must not build")):
        service = LLMService(provider=provider)
        assert service.provider is provider


def test_provider_built_once_and_cached():
    calls = []

    def fake_build():
        calls.append(1)
        return DummyLLMProvider()

    with patch.object(LLMService, "_build_provider", staticmethod(fake_build)):
        service = LLMService()
        p1 = service.provider
        p2 = service.provider
    assert p1 is p2
    assert len(calls) == 1
