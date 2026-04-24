"""
Singleton embedder — upgraded from all-MiniLM-L6-v2 to BAAI/bge-small-en-v1.5.

Why BGE-small over MiniLM:
- Same vector dimension (384) → existing FAISS indexes stay compatible
- Significantly better retrieval quality on BEIR benchmarks
- ~130MB model size (vs 80MB for MiniLM — acceptable tradeoff)
- BGE models require a query instruction prefix for retrieval tasks:
  encode queries with "Represent this sentence: " prefix
  encode documents without any prefix (already handled in indexer.py)
"""
from sentence_transformers import SentenceTransformer
from backend.config import EMBEDDING_MODEL

_embedder = None

def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        print(f"[Embedder] Loading model: {EMBEDDING_MODEL}")
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
        print(f"[Embedder] Model loaded. Dim={_embedder.get_sentence_embedding_dimension()}")
    return _embedder


def encode_query(embedder: SentenceTransformer, question: str):
    """
    Encode a retrieval query with BGE instruction prefix.
    BGE models perform best when queries use the prefix:
    'Represent this sentence: <query>'
    Falls back gracefully for non-BGE models.
    """
    import numpy as np
    from backend.config import EMBEDDING_MODEL
    if "bge" in EMBEDDING_MODEL.lower():
        question = "Represent this sentence: " + question
    q_emb = embedder.encode([question], normalize_embeddings=True)
    return np.array(q_emb, dtype=np.float32)


def encode_documents(embedder: SentenceTransformer, texts: list):
    """Encode document chunks — no prefix needed for BGE document encoding."""
    import numpy as np
    embs = embedder.encode(
        texts,
        batch_size=64,
        show_progress_bar=False,
        normalize_embeddings=True
    )
    return np.array(embs, dtype=np.float32)
