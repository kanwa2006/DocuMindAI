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
            logger.warning(
                f"[embedding] sentence_transformers not available ({e}). "
                "Falling back to GeminiEmbeddingProvider."
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
        import google.generativeai as genai
        keys_csv = os.getenv("GEMINI_API_KEYS", "")
        key = keys_csv.split(",")[0].strip() if keys_csv else os.getenv("GEMINI_API_KEY_1", "")
        if key:
            genai.configure(api_key=key)
        self._genai = genai
        logger.info("[embedding] GeminiEmbeddingProvider ready (text-embedding-004)")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            try:
                res = self._genai.embed_content(
                    model=self.MODEL,
                    content=text,
                    task_type="retrieval_document",
                )
                results.append(res["embedding"])
            except Exception as e:
                logger.warning(f"[embedding] Gemini embed failed: {e} — using zero vector")
                results.append([0.0] * 768)
        return results


class DummyEmbeddingProvider(BaseEmbeddingProvider):
    """Zero-vector fallback when no embedding backend is available."""
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        logger.warning("[embedding] DummyEmbeddingProvider — embeddings will be zero vectors")
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
