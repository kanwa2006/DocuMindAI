"""Regression tests for DEBUG_MASTER_PLAN M-4 + M-10.

The embedding chain silently degraded to zero vectors and the reranker
silently fabricated 0.85/0.99 scores — a "grounded" answer over either
looks fine but is meaningless. Degradation is now loud (ERROR logs) and
refused outright in production.
"""
import logging

import pytest

from app.services.embedding_service import (
    DummyEmbeddingProvider,
    GeminiEmbeddingProvider,
    EMBEDDING_DIM,
)
from app.services.reranker_service import DummyLocalReranker


# ── M-10: reranker ────────────────────────────────────────────────────────────

def test_dummy_reranker_refused_in_production(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="refused in production"):
        DummyLocalReranker().rerank("q", ["a", "b"])


def test_dummy_reranker_logs_error_outside_production(monkeypatch, caplog):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    with caplog.at_level(logging.ERROR, logger="app.services.reranker_service"):
        scores = DummyLocalReranker().rerank("q", ["a", "b", "c"])
    assert len(scores) == 3
    assert any("DEGRADED MODE" in r.message for r in caplog.records)


# ── M-4: embeddings ───────────────────────────────────────────────────────────

def test_gemini_embed_failure_raises_instead_of_zero_vector(monkeypatch):
    provider = GeminiEmbeddingProvider.__new__(GeminiEmbeddingProvider)

    class BrokenGenai:
        @staticmethod
        def embed_content(**kwargs):
            raise ConnectionError("gemini down")

    provider._genai = BrokenGenai()
    with pytest.raises(RuntimeError, match="zero-vector fallback is disabled"):
        provider.embed_documents(["some text"])


def test_dummy_embedding_provider_refused_in_production(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="refused in production"):
        DummyEmbeddingProvider().embed_documents(["t"])


def test_dummy_embedding_provider_loud_in_dev(monkeypatch, caplog):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    with caplog.at_level(logging.ERROR, logger="app.services.embedding_service"):
        vectors = DummyEmbeddingProvider().embed_documents(["t"])
    assert vectors == [[0.0] * EMBEDDING_DIM]
    assert any("DEGRADED MODE" in r.message for r in caplog.records)
