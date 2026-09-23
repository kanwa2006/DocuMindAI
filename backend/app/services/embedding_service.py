import logging
import os
from typing import List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Dimension used by BAAI/bge-m3.
# GeminiEmbeddingProvider requests the same dim via output_dimensionality so
# the Vector(1024) pgvector column and HNSW index never need rebuilding.
EMBEDDING_DIM = 1024

class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    MODEL_NAME = "BAAI/bge-m3"

    def __init__(self, model_name: str = None):
        model_name = model_name or self.MODEL_NAME
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"[embedding] Loading local model: {model_name}")
            self.model = SentenceTransformer(model_name)
            self._dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"[embedding] Dimension: {self._dim}")
            self._use_local = True
        except Exception as e:
            # M-4: the primary model being unavailable degrades every vector
            # in the corpus — this must be an alert-worthy signal, not an
            # info-level shrug.  The fallback (gemini-embedding-2 @
            # output_dimensionality=1024) produces native 1024-dim vectors
            # so it is self-consistent on a FRESH database; do NOT mix it
            # into a corpus that was already indexed with bge-m3.
            logger.error(
                f"[embedding] DEGRADED MODE — primary model {model_name} "
                f"unavailable ({e}). Falling back to GeminiEmbeddingProvider "
                "(gemini-embedding-2, output_dimensionality=1024). "
                "Self-consistent only on a fresh database — do not mix with "
                "existing bge-m3 vectors."
            )
            self._use_local = False
            self._fallback = GeminiEmbeddingProvider()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self._use_local:
            return self._fallback.embed_documents(texts)
        embeddings = self.model.encode(
            texts, show_progress_bar=False, normalize_embeddings=True
        )
        return embeddings.tolist()


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Uses gemini-embedding-2 with output_dimensionality=1024.

    text-embedding-004 was shut down on January 14 2026.  gemini-embedding-2
    supports Matryoshka Representation Learning (MRL) — we request exactly
    1024 dimensions to match the Vector(1024) pgvector column without any
    zero-padding.  This keeps index-time and query-time vectors identical.

    Supported output_dimensionality range: 128–3072.  Google recommends
    768, 1536, or 3072 for optimal retrieval quality; 1024 is valid and
    preserves backward compatibility with the existing DB schema.

    SDK: google-genai (google.genai), NOT the legacy google-generativeai.
    The new SDK binds the API key to the client object (no process global).
    """
    MODEL = "gemini-embedding-2"
    OUTPUT_DIM = EMBEDDING_DIM  # 1024 — must match Vector(1024) column

    def __init__(self):
        try:
            from google import genai as _genai
            from google.genai import types as _types
            self._genai = _genai
            self._types = _types
        except ImportError as exc:
            raise ImportError(
                "google-genai package is required for GeminiEmbeddingProvider. "
                "Install it with: pip install google-genai>=2.5.0"
            ) from exc

        # Resolve API key: prefer numbered env vars (key rotation), fall back
        # to the legacy GEMINI_API_KEYS comma-separated form.
        key = (
            os.getenv("GEMINI_API_KEY_1")
            or (os.getenv("GEMINI_API_KEYS", "").split(",")[0].strip())
            or os.getenv("GEMINI_API_KEY", "")
        )
        if not key:
            logger.warning(
                "[embedding] No Gemini API key found — GeminiEmbeddingProvider "
                "will raise on first embed call. Set GEMINI_API_KEY_1."
            )
        # Bind key to this client instance — no process-global side effects.
        self._client = self._genai.Client(api_key=key)
        logger.info(
            "[embedding] GeminiEmbeddingProvider ready "
            f"(model={self.MODEL}, output_dimensionality={self.OUTPUT_DIM})"
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            try:
                res = self._client.models.embed_content(
                    model=self.MODEL,
                    contents=text,
                    config=self._types.EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT",
                        # MRL truncation: request exactly 1024-dim to match
                        # the Vector(1024) pgvector column — no zero-padding.
                        output_dimensionality=self.OUTPUT_DIM,
                    ),
                )
                raw = list(res.embeddings[0].values)
                returned_dim = len(raw)
                # gemini-embedding-2 with output_dimensionality=1024 must
                # always return exactly 1024-dim vectors.  If the API ever
                # returns the wrong size, refuse rather than silently corrupt
                # the corpus (M-4 — zero-vector fallback is disabled).
                if returned_dim != EMBEDDING_DIM:
                    raise RuntimeError(
                        f"[embedding] gemini-embedding-2 returned {returned_dim}-dim "
                        f"vector but expected {EMBEDDING_DIM}-dim "
                        f"(output_dimensionality={self.OUTPUT_DIM}). "
                        "Refusing to insert a mis-sized vector into the pgvector column."
                    )
                results.append(raw)
            except Exception as e:
                # M-4: never silently index a zero vector — it poisons the
                # corpus with rows that match nothing (or everything at
                # distance ~1) while the document still reaches READY and
                # answers *look* grounded. Fail loud instead: the ingestion
                # worker retries and dead-letters to FAILED; the query path
                # surfaces an SSE error.
                logger.error(
                    f"[embedding] Gemini embed failed for text of length "
                    f"{len(text)}: {e} — refusing to emit a zero vector"
                )
                raise RuntimeError(
                    "Embedding generation failed and zero-vector fallback is disabled "
                    "(M-4). Check embedding model availability / Gemini keys."
                ) from e
        return results


class DummyEmbeddingProvider(BaseEmbeddingProvider):
    """Zero-vector test double. Never part of the automatic fallback chain —
    only usable when explicitly injected (tests). M-4: refuses in production."""
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        from app.core.config import settings
        if settings.ENVIRONMENT == "production":
            raise RuntimeError(
                "DummyEmbeddingProvider refused in production: zero vectors would "
                "poison the corpus while answers still look grounded (M-4)."
            )
        logger.error("[embedding] DEGRADED MODE — DummyEmbeddingProvider zero vectors in use")
        return [[0.0] * EMBEDDING_DIM for _ in texts]


class EmbeddingService:
    """Thin facade that selects a provider at construction time.

    Priority order:
      1. GeminiEmbeddingProvider — if EMBEDDING_PROVIDER=gemini (free-tier default)
      2. LocalEmbeddingProvider (BAAI/bge-m3) — primary, full quality
      3. GeminiEmbeddingProvider (gemini-embedding-2) — cloud fallback when local fails
      4. DummyEmbeddingProvider — test double only, never in production
    """

    def __init__(self):
        provider = os.getenv("EMBEDDING_PROVIDER", "local").lower()
        if provider == "gemini":
            logger.info("[embedding] EMBEDDING_PROVIDER=gemini — skipping local model, using GeminiEmbeddingProvider directly.")
            self._provider = GeminiEmbeddingProvider()
        else:
            self._provider = LocalEmbeddingProvider()

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self._provider.embed_documents(texts)


# Module-level singleton used by the API and Celery workers.
embedding_service = EmbeddingService()
