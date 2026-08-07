import logging
import os
from typing import List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Dimension used by BAAI/bge-m3 and mirrored in Gemini text-embedding-004
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
            # in the corpus (768-dim padded Gemini vs 1024-dim bge-m3) — this
            # must be an alert-worthy signal, not an info-level shrug.
            logger.error(
                f"[embedding] DEGRADED MODE — primary model {model_name} unavailable ({e}). "
                "Falling back to GeminiEmbeddingProvider (768-dim zero-padded to 1024; "
                "mixing with bge-m3 vectors harms similarity)."
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
    """Uses Gemini text-embedding-004 (768-dim, free-tier friendly)."""
    MODEL = "models/text-embedding-004"

    def __init__(self):
        # S5: this used to call `genai.configure(api_key=...)`, mutating the
        # SAME process-global the key rotator wrote to. In the worker process
        # it also raced the Beat-scheduled `auto_key_rotation`, which walks
        # every key and leaves the global set to whichever it tested last — so
        # embeddings went out on an arbitrary key and a 429 was attributed to
        # whichever key the rotator happened to think was current.
        #
        # Now the key is chosen per call and the client is bound to it.
        from app.services.gemini_client import get_client_pool
        self._pool = get_client_pool()
        logger.info("[embedding] GeminiEmbeddingProvider ready (text-embedding-004)")

    def _embed_one(self, text: str, task_type: str):
        """Embed on a healthy key, reporting failures against the key USED.

        Synchronous on purpose: this provider runs in the Celery worker and
        behind `run_in_executor` on the request path, so the rotator's blocking
        `get_key()` (the M-9 out-of-lock wait) is the correct primitive here —
        it is the async path that must never block, not this one.
        """
        from google.genai import types as genai_types
        from app.services.gemini_client import classify_failure
        from app.services.llm_key_rotation import get_key_rotator

        rotator = get_key_rotator()
        attempts = max(1, len(rotator.keys))
        last_exc = None
        for _ in range(attempts):
            key = rotator.get_key()
            try:
                res = self._pool.client_for(key).models.embed_content(
                    model=self.MODEL,
                    contents=text,
                    config=genai_types.EmbedContentConfig(task_type=task_type),
                )
                return list(res.embeddings[0].values)
            except Exception as exc:  # noqa: BLE001 - classified immediately
                last_exc = exc
                kind = classify_failure(exc)
                if kind == "rate_limit":
                    rotator.report_rate_limit(key, 300)
                elif kind == "invalid_key":
                    rotator.report_invalid_key(key)
                elif kind == "server_error":
                    rotator.report_rate_limit(key, 30)
                else:
                    raise
        raise RuntimeError(
            f"[embedding] all Gemini keys exhausted while embedding: {last_exc}"
        ) from last_exc

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            try:
                # S5: per-key client, and a 429 is now reported against the key
                # that actually served the call.
                raw = self._embed_one(text, task_type="retrieval_document")
                returned_dim = len(raw)
                # BUG-006 FIX: DocumentChunk.embedding is Vector(1024).
                # Gemini text-embedding-004 returns 768-dim vectors.
                # Pad to EMBEDDING_DIM with zeros so pgvector accepts the INSERT.
                # Retrieval works because the query embedding goes through the same
                # fallback chain and gets padded identically.
                if returned_dim < EMBEDDING_DIM:
                    raw = raw + [0.0] * (EMBEDDING_DIM - returned_dim)
                    logger.warning(
                        f"[embedding] GeminiEmbeddingProvider padded vector from "
                        f"{returned_dim}-dim to {EMBEDDING_DIM}-dim. "
                        "Primary BAAI/bge-m3 model may not be loaded — check worker startup logs."
                    )
                results.append(raw[:EMBEDDING_DIM])  # truncate if somehow larger
            except Exception as e:
                # M-4: never silently index a zero vector — it poisons the
                # corpus with rows that match nothing (or everything at
                # distance ~1) while the document still reaches READY and
                # answers *look* grounded. Fail loud instead: the ingestion
                # worker retries and dead-letters to FAILED; the query path
                # surfaces an SSE error.
                logger.error(f"[embedding] Gemini embed failed for text of length "
                             f"{len(text)}: {e} — refusing to emit a zero vector")
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
    def __init__(self, provider: BaseEmbeddingProvider = None):
        self.provider = provider or LocalEmbeddingProvider()

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return self.provider.embed_documents(texts)


# Singleton
embedding_service = EmbeddingService()
