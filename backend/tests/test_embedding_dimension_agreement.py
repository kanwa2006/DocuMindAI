"""Regression guard for final_audit S8 — silent corpus corruption.

When bge-m3 was unavailable, `LocalEmbeddingProvider` fell back to Gemini
`text-embedding-004` and zero-padded its 768-dim vectors to 1024. The code
justified that as safe because "the query embedding goes through the same
fallback chain and gets padded identically".

That holds ONLY if every process is in the same mode. The API container and
the Celery worker load models independently and nothing reconciles them. A
worker that fails to download bge-m3 while the API succeeds writes padded
Gemini document vectors which are then compared against real bge-m3 query
vectors.

The result is the dangerous kind of wrong: the cosine similarity is not zero
and not an error — it is a plausible number. Retrieval returns confidently
ranked irrelevant chunks, the reranker scores them, the trust score reports
MEDIUM, and every layer that might have caught it reports normally.

Nothing can detect that after the fact without per-chunk provenance (a
migration + re-index, parked as an owner decision). So it is prevented at the
source: in production the padded fallback REFUSES rather than writing a corpus
that cannot be told apart from a good one — the same precedent
`DummyEmbeddingProvider` already sets in this file for zero vectors (M-4).
"""
import importlib
import sys

import pytest

from app.core.config import settings as app_settings
from app.services import embedding_service as es_module
from app.services.embedding_service import (
    EMBEDDING_DIM,
    DummyEmbeddingProvider,
    EmbeddingService,
    LocalEmbeddingProvider,
)


class _FakeModel:
    def __init__(self, dim):
        self._dim = dim

    def get_sentence_embedding_dimension(self):
        return self._dim

    def encode(self, texts, **kwargs):
        import numpy as np

        return np.zeros((len(texts), self._dim))


def _install_fake_sentence_transformers(monkeypatch, dim):
    """Make `from sentence_transformers import SentenceTransformer` yield a fake."""
    mod = type(sys)("sentence_transformers")
    mod.SentenceTransformer = lambda name: _FakeModel(dim)
    monkeypatch.setitem(sys.modules, "sentence_transformers", mod)


def _force_model_load_failure(monkeypatch):
    mod = type(sys)("sentence_transformers")

    def _boom(name):
        raise RuntimeError("model download failed")

    mod.SentenceTransformer = _boom
    monkeypatch.setitem(sys.modules, "sentence_transformers", mod)


def test_a_model_with_the_wrong_dimension_fails_to_load(monkeypatch):
    """768-dim model + Vector(1024) column = silent corruption."""
    _install_fake_sentence_transformers(monkeypatch, dim=768)
    monkeypatch.setattr(app_settings, "ENVIRONMENT", "production", raising=False)

    with pytest.raises(RuntimeError) as exc:
        LocalEmbeddingProvider()

    assert "corrupt" in str(exc.value).lower() or "refus" in str(exc.value).lower(), (
        f"a dimension mismatch did not fail loudly: {exc.value}"
    )


def test_the_padded_fallback_is_refused_in_production(monkeypatch):
    """The core of S8: this process must not write vectors nobody can compare."""
    _force_model_load_failure(monkeypatch)
    monkeypatch.setattr(app_settings, "ENVIRONMENT", "production", raising=False)

    with pytest.raises(RuntimeError) as exc:
        LocalEmbeddingProvider()

    message = str(exc.value)
    assert "production" in message or "corrupt" in message, (
        "the zero-padded Gemini fallback was accepted in production. A worker "
        "in that mode writes 768-dim-padded vectors while the API queries with "
        "real 1024-dim ones, and their similarity is plausible garbage (S8)."
    )


def test_the_fallback_is_still_allowed_outside_production(monkeypatch):
    """Refusing everywhere would make local development impossible."""
    _force_model_load_failure(monkeypatch)
    monkeypatch.setattr(app_settings, "ENVIRONMENT", "development", raising=False)
    monkeypatch.setattr(
        es_module, "GeminiEmbeddingProvider", lambda: object(), raising=True
    )

    provider = LocalEmbeddingProvider()
    assert provider._use_local is False, "expected the degraded fallback path"


def test_the_active_embedding_model_is_reportable(monkeypatch):
    """A mismatch across containers must at least be DIAGNOSABLE."""
    _install_fake_sentence_transformers(monkeypatch, dim=EMBEDDING_DIM)
    service = EmbeddingService(LocalEmbeddingProvider())

    sig = service.signature
    assert "bge-m3" in sig and str(EMBEDDING_DIM) in sig, (
        f"signature does not identify the model and dimension: {sig!r}. "
        "Comparing this across the API and worker is how a silent mismatch "
        "gets found."
    )


def test_a_degraded_process_reports_a_different_signature(monkeypatch):
    """The two modes must not look identical in diagnostics."""
    _install_fake_sentence_transformers(monkeypatch, dim=EMBEDDING_DIM)
    healthy = EmbeddingService(LocalEmbeddingProvider()).signature

    _force_model_load_failure(monkeypatch)
    monkeypatch.setattr(app_settings, "ENVIRONMENT", "development", raising=False)
    monkeypatch.setattr(
        es_module, "GeminiEmbeddingProvider", lambda: object(), raising=True
    )
    degraded = EmbeddingService(LocalEmbeddingProvider()).signature

    assert healthy != degraded, (
        "a process writing padded Gemini vectors reports the SAME signature as "
        "one writing real bge-m3 vectors, so comparing them across containers "
        "proves nothing (S8)."
    )
    assert "FALLBACK" in degraded


def test_dummy_provider_still_refuses_in_production(monkeypatch):
    """The precedent this fix follows must not itself regress (M-4)."""
    from app.core.config import settings as real_settings

    monkeypatch.setattr(real_settings, "ENVIRONMENT", "production", raising=False)
    with pytest.raises(RuntimeError):
        DummyEmbeddingProvider().embed_documents(["x"])
