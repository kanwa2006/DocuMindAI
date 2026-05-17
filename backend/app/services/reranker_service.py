import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class BaseRerankerProvider(ABC):
    @abstractmethod
    def rerank(self, query: str, documents: List[str]) -> List[float]:
        """Abstract method to score the relevance of documents to a query."""
        pass

class DummyLocalReranker(BaseRerankerProvider):
    def rerank(self, query: str, documents: List[str]) -> List[float]:
        """
        Placeholder local reranker to satisfy architecture without heavy pip dependencies.
        In production, this would be replaced with a CrossEncoder or Cohere Rerank API.
        """
        logger.info(f"[Tracing] Running dummy local reranking for {len(documents)} candidates.")
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

reranker_service = RerankerService()
