"""
Per-user FAISS index with hybrid retrieval (dense semantic + BM25 keyword).

Improvements over previous version:
- Page number stored in every chunk's metadata
- BM25 keyword search combined with FAISS cosine similarity
- Final ranking: 70% semantic + 30% keyword (normalized)
- Diversity-aware deduplication retained
"""
import os
import re
import json
import math
import numpy as np
import faiss
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.qa.embedder import get_embedder, encode_query, encode_documents
from backend.documents.storage import get_index_dir
from backend.config import CHUNK_SIZE, CHUNK_OVERLAP

METADATA_FILE = "chunks.json"
INDEX_FILE    = "faiss.index"


# ── BM25 ──────────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list:
    return re.findall(r'\b\w+\b', (text or "").lower())


def _bm25_scores(query: str, documents: list, k1: float = 1.5, b: float = 0.75) -> list:
    """Return BM25 score for each document string."""
    query_terms = _tokenize(query)
    N = len(documents)
    if not query_terms or N == 0:
        return [0.0] * N

    tokenized = [_tokenize(d) for d in documents]
    avg_len = sum(len(t) for t in tokenized) / max(N, 1)

    idf: dict = {}
    for term in set(query_terms):
        df = sum(1 for t in tokenized if term in set(t))
        idf[term] = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

    scores = []
    for doc_tokens in tokenized:
        score = 0.0
        doc_len = len(doc_tokens)
        tf_map: dict = {}
        for t in doc_tokens:
            tf_map[t] = tf_map.get(t, 0) + 1
        for term in query_terms:
            tf = tf_map.get(term, 0)
            if tf > 0:
                num = tf * (k1 + 1)
                den = tf + k1 * (1 - b + b * doc_len / max(avg_len, 1))
                score += idf.get(term, 0) * (num / den)
        scores.append(score)
    return scores


def _normalize(scores: list) -> list:
    if not scores:
        return scores
    mn, mx = min(scores), max(scores)
    if mx == mn:
        return [0.5] * len(scores)
    return [(s - mn) / (mx - mn) for s in scores]


_cross_encoder = None  # lazy-loaded singleton


def _get_cross_encoder():
    """Load cross-encoder model once, return None if unavailable."""
    global _cross_encoder
    if _cross_encoder is not None:
        return _cross_encoder
    try:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            max_length=512
        )
        print("[Reranker] Cross-encoder loaded.")
    except Exception as e:
        print(f"[Reranker] Cross-encoder unavailable: {e}")
        _cross_encoder = False  # mark as failed so we don't retry
    return _cross_encoder


def _rerank_chunks(question: str, chunks: list, top_k: int) -> list:
    """
    Optional reranking pass using a cross-encoder.
    Takes top candidates from hybrid search, re-scores them, returns best top_k.
    Falls back silently if model is not available.
    """
    if not chunks:
        return chunks
    model = _get_cross_encoder()
    if not model:
        return chunks[:top_k]
    try:
        pairs  = [(question, c.get("chunk", "")) for c in chunks]
        scores = model.predict(pairs)
        ranked = sorted(zip(scores, chunks), key=lambda x: -x[0])
        return [c for _, c in ranked[:top_k]]
    except Exception as e:
        print(f"[Reranker Error] {e}")
        return chunks[:top_k]


# ── Chunk utilities ────────────────────────────────────────────────────────────

def _chunk_signature(text: str) -> str:
    if not text:
        return ""
    compact = " ".join(text.lower().split())
    if len(compact) <= 320:
        return compact
    mid = len(compact) // 2
    return compact[:120] + "|" + compact[mid - 60: mid + 60] + "|" + compact[-120:]


def _assign_page_numbers(full_text: str, chunks: list) -> list:
    """
    Assign a [Page N] number to each chunk by locating it in the full text.
    Returns list of (chunk_text, page_num).
    """
    markers = [(m.start(), int(m.group(1)))
               for m in re.finditer(r'\[Page (\d+)\]', full_text)]
    if not markers:
        return [(c, 1) for c in chunks]

    result = []
    search_from = 0
    for chunk in chunks:
        probe = chunk[:60].strip()
        idx = full_text.find(probe, search_from)
        if idx == -1:
            idx = search_from
        page_num = 1
        for pos, pg in markers:
            if pos <= idx:
                page_num = pg
            else:
                break
        result.append((chunk, page_num))
        search_from = max(0, idx + max(len(probe) // 2, 1))
    return result


def _select_diverse(ranked_indices: list, metadata: list, limit: int) -> list:
    selected, seen = [], set()
    for idx in ranked_indices:
        if not (0 <= idx < len(metadata)):
            continue
        sig = _chunk_signature(metadata[idx].get("chunk", ""))
        if not sig or sig in seen:
            continue
        seen.add(sig)
        selected.append(metadata[idx])
        if len(selected) >= limit:
            break
    return selected


# ── Index paths ────────────────────────────────────────────────────────────────

def _get_paths(user_id: int):
    idx_dir = get_index_dir(user_id)
    return os.path.join(idx_dir, INDEX_FILE), os.path.join(idx_dir, METADATA_FILE)


# ── Build ──────────────────────────────────────────────────────────────────────

def is_already_indexed(user_id: int, source_filename: str) -> bool:
    """Check if a source file is already in the user's index — prevents duplicate processing."""
    _, meta_path = _get_paths(user_id)
    if not os.path.exists(meta_path):
        return False
    source_base = os.path.basename(source_filename)
    parts = source_base.split("_", 1)
    if len(parts) == 2 and len(parts[0]) == 32 and parts[0].isalnum():
        source_base = parts[1]
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        return any(m.get("source") == source_base for m in metadata)
    except Exception:
        return False


def build_user_index(user_id: int, new_text: str, source_filename: str,
                     force_reindex: bool = False):
    """
    Chunk, embed (batched) and add document to user's FAISS index.
    Phase 1 improvements:
    - Skips re-indexing if source already indexed (shared cache — one upload, many views)
    - Batch embedding: all chunks embedded in one call (safe speed boost, no accuracy loss)
    """
    if not new_text or not new_text.strip():
        print(f"[Indexer] Empty text for {source_filename}, skipping")
        return

    # ── Shared cache: skip if already indexed ──────────────────────────────────
    if not force_reindex and is_already_indexed(user_id, source_filename):
        print(f"[Indexer] ✅ Already indexed {source_filename} — skipping duplicate processing")
        return

    index_path, meta_path = _get_paths(user_id)
    embedder = get_embedder()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_text(new_text)
    if not chunks:
        print(f"[Indexer] No chunks for {source_filename}")
        return

    # Assign page numbers before embedding
    chunk_pages = _assign_page_numbers(new_text, chunks)

    # ── Batch embedding: all chunks at once (safe speed boost) ─────────────────
    # Batch size 64 is safe for most machines; reduces per-chunk overhead significantly
    BATCH_SIZE = 64
    all_embeddings = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        batch_emb = encode_documents(embedder, batch)
        all_embeddings.append(batch_emb)
    embeddings = np.vstack(all_embeddings) if all_embeddings else encode_documents(embedder, chunks)
    print(f"[Indexer] Batch-embedded {len(chunks)} chunks in {len(all_embeddings)} batches")

    if os.path.exists(index_path):
        index = faiss.read_index(index_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        index = faiss.IndexFlatIP(embeddings.shape[1])
        metadata = []

    index.add(embeddings)

    # Clean UUID prefix from filename
    source_base = os.path.basename(source_filename)
    parts = source_base.split("_", 1)
    if len(parts) == 2 and len(parts[0]) == 32 and parts[0].isalnum():
        source_base = parts[1]

    for chunk_text, page_num in chunk_pages:
        metadata.append({"chunk": chunk_text, "source": source_base, "page": page_num})

    faiss.write_index(index, index_path)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False)

    print(f"[Indexer] ✅ Indexed {len(chunks)} chunks from {source_base}")


# ── Hybrid Query ───────────────────────────────────────────────────────────────

def query_user_index(user_id: int, question: str, top_k: int = 5,
                     source_filter: list = None) -> list:
    """
    Hybrid retrieval: 70% FAISS (semantic) + 30% BM25 (keyword).
    Returns top-k diverse chunks with page metadata.
    """
    index_path, meta_path = _get_paths(user_id)
    if not os.path.exists(index_path):
        return []

    embedder = get_embedder()
    index = faiss.read_index(index_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    if not metadata:
        return []

    # Build active subset (source filter)
    if source_filter:
        filter_names = [f.lower().strip() for f in source_filter]
        active_idx = [i for i, m in enumerate(metadata)
                      if any(fn in m.get("source", "").lower() for fn in filter_names)]
    else:
        active_idx = list(range(len(metadata)))

    if not active_idx:
        return []

    active_meta = [metadata[i] for i in active_idx]
    active_texts = [m.get("chunk", "") for m in active_meta]

    # ── FAISS semantic search ─────────────────────────────────────────────────
    # Encode query with BGE instruction prefix if applicable
    q_emb = encode_query(embedder, question)
    pool_k = min(max(top_k * 4, 20), len(active_idx))

    if source_filter:
        dim = index.d
        sub = faiss.IndexFlatIP(dim)
        vecs = np.zeros((len(active_idx), dim), dtype=np.float32)
        for j, fi in enumerate(active_idx):
            index.reconstruct(fi, vecs[j])
        sub.add(vecs)
        dists, hits = sub.search(q_emb, pool_k)
    else:
        dists, hits = index.search(q_emb, pool_k)

    faiss_scores = [0.0] * len(active_meta)
    for rank, hit in enumerate(hits[0]):
        if 0 <= hit < len(active_meta):
            faiss_scores[hit] = float(dists[0][rank])

    # ── BM25 keyword search ───────────────────────────────────────────────────
    bm25_raw = _bm25_scores(question, active_texts)

    # ── Hybrid combine ────────────────────────────────────────────────────────
    fn = _normalize(faiss_scores)
    bn = _normalize(bm25_raw)
    combined = [0.7 * f + 0.3 * b for f, b in zip(fn, bn)]
    ranked = sorted(range(len(active_meta)), key=lambda i: -combined[i])

    # Step 1: diverse top candidates from hybrid search (wider pool)
    candidates = _select_diverse(ranked, active_meta, min(top_k * 3, len(active_meta)))
    # Step 2: rerank with cross-encoder, return final top_k
    return _rerank_chunks(question, candidates, top_k)


# ── Remove / Delete ────────────────────────────────────────────────────────────

def _remove_chunks_for_file(user_id: int, filename: str):
    index_path, meta_path = _get_paths(user_id)
    if not os.path.exists(meta_path):
        return

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    source_base = os.path.basename(filename)
    parts = source_base.split("_", 1)
    if len(parts) == 2 and len(parts[0]) == 32 and parts[0].isalnum():
        source_base = parts[1]

    keep = [i for i, m in enumerate(metadata) if m.get("source") != source_base]
    if len(keep) == len(metadata):
        return
    if not keep:
        for p in [index_path, meta_path]:
            if os.path.exists(p):
                os.remove(p)
        return

    if os.path.exists(index_path):
        old = faiss.read_index(index_path)
        dim = old.d
        new_index = faiss.IndexFlatIP(dim)
        vecs = np.zeros((len(keep), dim), dtype=np.float32)
        for j, i in enumerate(keep):
            old.reconstruct(i, vecs[j])
        new_index.add(vecs)
        faiss.write_index(new_index, index_path)

    new_meta = [metadata[i] for i in keep]
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(new_meta, f, ensure_ascii=False)


def delete_user_index(user_id: int):
    for p in _get_paths(user_id):
        if os.path.exists(p):
            os.remove(p)
