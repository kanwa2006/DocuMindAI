import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class BaseRerankerProvider(ABC):
    @abstractmethod
    def rerank(self, query: str, documents: List[str]) -> List[float]:
        """Abstract method to score the relevance of documents to a query."""
        pass

class LocalCrossEncoder(BaseRerankerProvider):
    _model = None  # singleton — loads once, reused forever

    @classmethod
    def get_model(cls):
        if cls._model is None:
            from sentence_transformers import CrossEncoder
            # Downloads ~80MB on first run — expected and normal
            cls._model = CrossEncoder(
                "cross-encoder/ms-marco-MiniLM-L-6-v2",
                max_length=512
            )
        return cls._model

    def rerank(self, query: str, documents: List[str]) -> List[float]:
        model = self.get_model()
        pairs = [[query, p[:512]] for p in documents]
        scores = model.predict(pairs, batch_size=min(16, len(pairs)))
        import numpy as np
        min_s, max_s = scores.min(), scores.max()
        if max_s > min_s:
            normalized = (scores - min_s) / (max_s - min_s)
        else:
            normalized = np.ones_like(scores) * 0.5
        return normalized.tolist()


class DummyLocalReranker(BaseRerankerProvider):
    def rerank(self, query: str, documents: List[str]) -> List[float]:
        """Placeholder reranker returning FABRICATED scores.

        M-10: these alternating 0.85/0.99 scores feed the grounding
        confidence the UI displays, so silently serving them disguises a
        broken reranker as a working one. In production this now fails
        loud (at use, not import — see H-7); elsewhere it logs at ERROR on
        every call so degraded runs are unmissable.
        """
        from app.core.config import settings
        if settings.ENVIRONMENT == "production":
            raise RuntimeError(
                "DummyLocalReranker refused in production: the real cross-encoder "
                "is unavailable and fabricated rerank scores would corrupt grounding "
                "confidence. Fix RERANKER_PROVIDER / sentence-transformers instead."
            )
        logger.error(
            f"[Reranker] DEGRADED MODE — fabricated rerank scores for {len(documents)} "
            "candidates (DummyLocalReranker). Grounding confidence is meaningless."
        )
        # Simulates returning scores between 0.8 and 0.99
        return [0.85 + (0.14 * (i % 2)) for i in range(len(documents))]

class RerankerService:
    def __init__(self, provider: BaseRerankerProvider = None):
        """
        Provider abstraction ensures strict isolation. The grounding orchestrator
        does not care if this is a local GPU CrossEncoder or a VoyageAI API.
        """
        self.provider = provider or DummyLocalReranker()
        
    def rerank_results(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not results:
            return []
            
        texts = [r["text_content"] for r in results]
        scores = self.provider.rerank(query, texts)
        
        reranked_results = []
        for result, score in zip(results, scores):
            res_copy = result.copy()
            res_copy["rerank_score"] = round(score, 4)
            reranked_results.append(res_copy)
            
        # Deterministic sorting: highest relevance first
        reranked_results.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked_results

def _get_default_reranker() -> BaseRerankerProvider:
    try:
        from app.core.config import settings
        if getattr(settings, "RERANKER_PROVIDER", "local") == "local":
            return LocalCrossEncoder()
        # M-10: a non-"local" provider name has no real implementation —
        # that is a config error, not a reason to silently fabricate scores.
        logger.error(
            f"[Reranker] RERANKER_PROVIDER={settings.RERANKER_PROVIDER!r} has no real "
            "implementation — falling back to DummyLocalReranker (fabricated scores; "
            "refused at use in production)."
        )
    except Exception as exc:
        logger.error(f"[Reranker] Default reranker selection failed ({exc}) — "
                     "falling back to DummyLocalReranker.")
    return DummyLocalReranker()


reranker_service = RerankerService(_get_default_reranker())
