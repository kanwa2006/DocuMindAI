import logging
import time
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.document_chunk import DocumentChunk
from app.services.embedding_service import embedding_service
from app.core.config import settings
import numpy as np

logger = logging.getLogger(__name__)

# H-1: the misleading `import faiss` is gone — FAISS was never used and was
# not a dependency; the non-pgvector branch below is a NumPy scan. Warn once
# per process when that dev-only fallback is active.
_numpy_fallback_warned = False

class RetrievalService:
    @staticmethod
    async def retrieve_chunks(
        db: AsyncSession,
        query: str,
        workspace_id: Optional[UUID] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        document_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """
        Hybrid Retrieval Orchestrator.
        Executes parallel Semantic (pgvector) and Lexical (tsvector BM25) searches, 
        then fuses the candidate lists using Reciprocal Rank Fusion (RRF).
        """
        start_time = time.time()
        logger.info(f"[Tracing] Starting hybrid retrieval for: '{query}' (top_k={top_k})")
        
        # We fetch a deeper candidate pool (e.g. 30) for fusion to ensure robust reranking coverage
        fusion_k = max(top_k * 2, 30)
        
        # --- 1. Semantic (Vector) Retrieval ---
        embed_start = time.time()
        query_vector = embedding_service.generate_embeddings([query])[0]
        embed_duration = time.time() - embed_start
        
        if settings.VECTOR_BACKEND == "pgvector":
            distance_expr = DocumentChunk.embedding.cosine_distance(query_vector).label('distance')
            similarity_expr = (1 - distance_expr).label('similarity')
            
            stmt_vec = (
                select(DocumentChunk, DocumentPage.page_number, Document.filename, similarity_expr)
                .join(Document, DocumentChunk.document_id == Document.id)
                .join(DocumentPage, DocumentChunk.page_id == DocumentPage.id)
            )
            
            if workspace_id:
                stmt_vec = stmt_vec.where(Document.workspace_id == workspace_id)
            if document_ids:
                stmt_vec = stmt_vec.where(Document.id.in_(document_ids))
            stmt_vec = stmt_vec.where(Document.status == "READY")
            if similarity_threshold > 0.0:
                stmt_vec = stmt_vec.where((1 - DocumentChunk.embedding.cosine_distance(query_vector)) >= similarity_threshold)
                
            stmt_vec = stmt_vec.order_by(distance_expr).limit(fusion_k)
        else:
            # Dev-only NumPy fallback (labelled "faiss" historically; FAISS
            # was never actually used). O(N) memory+compute per query.
            global _numpy_fallback_warned
            if not _numpy_fallback_warned:
                logger.warning(
                    f"[Retrieval] VECTOR_BACKEND={settings.VECTOR_BACKEND!r} uses the "
                    "in-memory NumPy scan — dev-only; set VECTOR_BACKEND=pgvector for "
                    "indexed ANN retrieval."
                )
                _numpy_fallback_warned = True
            stmt_vec = (
                select(DocumentChunk, DocumentPage.page_number, Document.filename)
                .join(Document, DocumentChunk.document_id == Document.id)
                .join(DocumentPage, DocumentChunk.page_id == DocumentPage.id)
            )
            if workspace_id:
                stmt_vec = stmt_vec.where(Document.workspace_id == workspace_id)
            if document_ids:
                stmt_vec = stmt_vec.where(Document.id.in_(document_ids))
            stmt_vec = stmt_vec.where(Document.status == "READY")
        
        # --- 2. Lexical (BM25-style FTS or Fallback) ---
        if "sqlite" in settings.async_database_url:
            # SQLite does not support func.websearch_to_tsquery natively without fts5 setup
            # Simple ILIKE fallback for SQLite
            lexical_rank_expr = func.length(DocumentChunk.text_content).label('lexical_rank') # Mock rank
            stmt_lex = (
                select(DocumentChunk, DocumentPage.page_number, Document.filename, lexical_rank_expr)
                .join(Document, DocumentChunk.document_id == Document.id)
                .join(DocumentPage, DocumentChunk.page_id == DocumentPage.id)
            )
            if workspace_id:
                stmt_lex = stmt_lex.where(Document.workspace_id == workspace_id)
            stmt_lex = stmt_lex.where(Document.status == "READY")
            stmt_lex = stmt_lex.where(DocumentChunk.text_content.ilike(f"%{query}%"))
            stmt_lex = stmt_lex.limit(fusion_k)
        else:
            ts_query = func.websearch_to_tsquery('english', query)
            ts_vector = func.to_tsvector('english', DocumentChunk.text_content)
            lexical_rank_expr = func.ts_rank_cd(ts_vector, ts_query).label('lexical_rank')
            
            stmt_lex = (
                select(DocumentChunk, DocumentPage.page_number, Document.filename, lexical_rank_expr)
                .join(Document, DocumentChunk.document_id == Document.id)
                .join(DocumentPage, DocumentChunk.page_id == DocumentPage.id)
            )
            
            if workspace_id:
                stmt_lex = stmt_lex.where(Document.workspace_id == workspace_id)
            if document_ids:
                stmt_lex = stmt_lex.where(Document.id.in_(document_ids))
            stmt_lex = stmt_lex.where(Document.status == "READY")
            
            stmt_lex = stmt_lex.where(ts_vector.op('@@')(ts_query))
            stmt_lex = stmt_lex.order_by(lexical_rank_expr.desc()).limit(fusion_k)
        
        # --- 3. Execute Queries ---
        db_start = time.time()
        
        result_vec = await db.execute(stmt_vec)
        if settings.VECTOR_BACKEND == "pgvector":
            rows_vec = result_vec.all()
        else:
            # Perform memory FAISS/Numpy cosine similarity
            all_rows = result_vec.all()
            if all_rows:
                embeddings = np.array([r.DocumentChunk.embedding for r in all_rows])
                q_vec = np.array(query_vector)
                # Compute cosine similarities
                dot_products = np.dot(embeddings, q_vec)
                norms = np.linalg.norm(embeddings, axis=1) * np.linalg.norm(q_vec)
                similarities = dot_products / (norms + 1e-9)
                
                # Filter & Sort
                valid_indices = np.where(similarities >= similarity_threshold)[0]
                sorted_idx = valid_indices[np.argsort(-similarities[valid_indices])][:fusion_k]
                
                rows_vec = []
                for idx in sorted_idx:
                    r = all_rows[idx]
                    rows_vec.append((r.DocumentChunk, r.page_number, r.filename, float(similarities[idx])))
            else:
                rows_vec = []
        
        result_lex = await db.execute(stmt_lex)
        rows_lex = result_lex.all()
        
        db_duration = time.time() - db_start
        
        # --- 4. Reciprocal Rank Fusion (RRF) ---
        rrf_k = 60 # Standard smoothing constant to prevent high-ranked outliers from dominating
        fused_scores = {}
        chunk_metadata = {}
        
        # Process Vector Ranks
        for rank, (chunk, page_number, filename, similarity) in enumerate(rows_vec):
            chunk_id = str(chunk.id)
            if chunk_id not in chunk_metadata:
                chunk_metadata[chunk_id] = {
                    "chunk_id": chunk_id, "document_id": str(chunk.document_id),
                    "filename": filename, "page_number": page_number,
                    "chunk_index": chunk.chunk_index, "text_content": chunk.text_content,
                    "similarity_score": round(similarity, 4), "lexical_score": 0.0,
                    "layout_metadata": chunk.chunk_metadata
                }
                fused_scores[chunk_id] = 0.0
            fused_scores[chunk_id] += 1.0 / (rrf_k + rank + 1)
            
        # Process Lexical Ranks
        for rank, (chunk, page_number, filename, lexical_score) in enumerate(rows_lex):
            chunk_id = str(chunk.id)
            if chunk_id not in chunk_metadata:
                chunk_metadata[chunk_id] = {
                    "chunk_id": chunk_id, "document_id": str(chunk.document_id),
                    "filename": filename, "page_number": page_number,
                    "chunk_index": chunk.chunk_index, "text_content": chunk.text_content,
                    "similarity_score": 0.0, "lexical_score": round(lexical_score, 4),
                    "layout_metadata": chunk.chunk_metadata
                }
                fused_scores[chunk_id] = 0.0
            else:
                chunk_metadata[chunk_id]["lexical_score"] = round(lexical_score, 4)
                
            fused_scores[chunk_id] += 1.0 / (rrf_k + rank + 1)
            
        # --- 5. Sort & Truncate ---
        sorted_chunks = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)
        final_results = []
        for cid in sorted_chunks[:top_k]:
            meta = chunk_metadata[cid]
            meta["rrf_score"] = round(fused_scores[cid], 4)
            final_results.append(meta)
            
        total_duration = time.time() - start_time
        logger.info(f"[Tracing] Hybrid Retrieval complete. Fused {len(fused_scores)} candidates down to {len(final_results)} in {total_duration:.4f}s.")
        
        return {
            "query": query,
            "results": final_results,
            "tracing": {
                "embedding_time_sec": round(embed_duration, 4),
                "database_time_sec": round(db_duration, 4),
                "total_time_sec": round(total_duration, 4),
                "semantic_candidates_found": len(rows_vec),
                "lexical_candidates_found": len(rows_lex),
                "fused_unique_candidates": len(fused_scores)
            }
        }
