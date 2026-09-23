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
            # S8: a model whose dimension disagrees with the column would write
            # vectors that pgvector accepts only after padding/truncation, and
            # every similarity computed against them is then meaningless while
            # still looking like a number. Fail at load, not per document.
            if self._dim != EMBEDDING_DIM:
                raise RuntimeError(
                    f"[embedding] {model_name} produces {self._dim}-dim vectors but "
                    f"DocumentChunk.embedding is Vector({EMBEDDING_DIM}). Mixing "
                    "dimensions silently corrupts the corpus — refusing to start."
                )
            self._use_local = True
        except Exception as e:
            # M-4: the primary model being unavailable degrades every vector
            # in the corpus (768-dim padded Gemini vs 1024-dim bge-m3) — this
            # must be an alert-worthy signal, not an info-level shrug.
            # S8: the padded-Gemini fallback is SAFE ONLY IF EVERY PROCESS IS IN
            # THE SAME MODE. The API container and the Celery worker load models
            # independently, and nothing reconciles them. A worker that fails to
            # download bge-m3 while the API succeeds writes 768-dim vectors
            # zero-padded to 1024, which are then compared against real 1024-dim
            # bge-m3 query vectors. That cosine similarity is not zero — it is
            # PLAUSIBLE GARBAGE. Retrieval returns confidently ranked irrelevant
            # chunks, and every downstream signal that might have caught it
            # (rerank scores, trust score) reports normally.
            #
            # Nothing can detect that after the fact without per-chunk
            # provenance, so the corruption must be prevented at the source:
            # in production this refuses rather than silently producing a corpus
            # that cannot be told apart from a good one. Same precedent, same
            # file — DummyEmbeddingProvider already refuses in production for
            # exactly this reason (M-4).
            from app.core.config import settings as _settings

            if _settings.ENVIRONMENT == "production":
                logger.critical(
                    "[embedding] primary model %s unavailable (%s). REFUSING to fall "
                    "back to zero-padded Gemini vectors in production: this process "
                    "would write a corpus that silently disagrees with every other "
                    "process's vectors (S8).",
                    model_name, e,
                )
                raise RuntimeError(
                    f"[embedding] primary model {model_name} unavailable ({e}) and the "
                    "zero-padded Gemini fallback is disabled in production — it would "
                    "corrupt the corpus undetectably. Fix model availability, then "
                    "restart. Documents already embedded by this process must be "
                    "re-indexed."
                ) from e

            logger.error(
                f"[embedding] DEGRADED MODE — primary model {model_name} unavailable ({e}). "
                "Falling back to GeminiEmbeddingProvider (768-dim zero-padded to 1024; "
                "mixing with bge-m3 vectors harms similarity). This is permitted ONLY "
                f"because ENVIRONMENT={_settings.ENVIRONMENT!r} is not production."
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
    supports Matryoshka Representation Learning (MRL), so we can request
    exactly 1024 dimensions — matching the pgvector Vector(1024) column —
    without any zero-padding.  This makes the fallback chain self-consistent:
    index-time and query-time embeddings are identical 1024-dim vectors.
    Supported range: 128–3072.  Google recommends 768, 1536, or 3072 for
    optimal retrieval quality; 1024 is valid and preserves backward
    compatibility with the existing corpus schema.
    """
    MODEL = "gemini-embedding-2"
    OUTPUT_DIM = EMBEDDING_DIM  # 1024 — must match Vector(1024) column

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
        logger.info(
            "[embedding] GeminiEmbeddingProvider ready (gemini-embedding-2, "
            f"output_dimensionality={self.OUTPUT_DIM})"
        )

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
                    config=genai_types.EmbedContentConfig(
                        task_type=task_type,
                        # MRL truncation: request exactly 1024-dim so we match
                        # the Vector(1024) pgvector column without any padding.
                        output_dimensionality=self.OUTPUT_DIM,
                    ),
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
                # RETRIEVAL_DOCUMENT is the task_type string accepted by
                # gemini-embedding-2 for indexing document chunks.
                raw = self._embed_one(text, task_type="RETRIEVAL_DOCUMENT")
                returned_dim = len(raw)
                # gemini-embedding-2 with output_dimensionality=1024 must always
                # return exactly 1024-dim vectors.  If the API ever returns the
                # wrong size, refuse rather than silently corrupt the corpus (M-4).
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

    @property
    def signature(self) -> str:
        """Which embedding model THIS process is actually using.

        S8: the API container and the Celery worker load models independently
        and nothing reconciles them. Vectors produced under different providers
        are not comparable, but their cosine similarity is a plausible number
        rather than an obvious error, so the mismatch is invisible in results.

        Exposing the signature does not fix that — a full fix records
        provenance per chunk and refuses at query time, which needs a migration
        and a re-index (owner decision, see PROGRESS.md). It makes the mismatch
        DIAGNOSABLE: compare this value across `/health` on the API and the
        worker, and a disagreement is the answer to "why is retrieval bad?"
        """
        provider = self.provider
        name = type(provider).__name__
        if isinstance(provider, LocalEmbeddingProvider):
            if getattr(provider, "_use_local", False):
                return f"{name}:{provider.MODEL_NAME}:{provider._dim}"
            # Degraded: this process writes padded Gemini vectors.
            return f"{name}:FALLBACK->GeminiEmbeddingProvider:padded-{EMBEDDING_DIM}"
        return f"{name}:{EMBEDDING_DIM}"


# Singleton
embedding_service = EmbeddingService()
