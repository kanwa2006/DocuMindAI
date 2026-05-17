import logging
from typing import List
from abc import ABC, abstractmethod
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Abstract method to embed a batch of documents."""
        pass

class LocalEmbeddingProvider(BaseEmbeddingProvider):
    # FIX 0.12: Upgraded to BAAI/bge-m3
    # 568M params | multilingual (100+ langs) | 8192 token context
    # dense + sparse retrieval simultaneously | ~1.2GB download on first run
    # Fallback: nomic-ai/nomic-embed-text-v1.5 (274MB, CPU-only)
    MODEL_NAME = "BAAI/bge-m3"

    def __init__(self, model_name: str = None):
        model_name = model_name or self.MODEL_NAME
        logger.info(f"[embedding] Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        dims = self.model.get_sentence_embedding_dimension()
        logger.info(f"[embedding] Model ready — {model_name} | dims={dims}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        logger.info(f"[embedding] Embedding {len(texts)} chunks via {self.MODEL_NAME}")
        embeddings = self.model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return embeddings.tolist()


class EmbeddingService:
    def __init__(self, provider: BaseEmbeddingProvider = None):
        """
        Provider abstraction allows hot-swapping to OpenAI/Voyage/Instructor later.
        """
        self.provider = provider or LocalEmbeddingProvider()
        
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return self.provider.embed_documents(texts)

# Singleton instance for worker use
embedding_service = EmbeddingService()
