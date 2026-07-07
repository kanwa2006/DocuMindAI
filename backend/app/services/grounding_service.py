import logging
import time
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.retrieval_service import RetrievalService
from app.services.reranker_service import reranker_service

logger = logging.getLogger(__name__)

class GroundingService:
    @staticmethod
    async def prepare_grounded_context(
        db: AsyncSession,
        query: str,
        workspace_id: Optional[UUID] = None,
        retrieval_top_k: int = 30,          # Candidate Expansion
        final_top_k: int = 5,               # Selection Limit
        similarity_threshold: float = 0.0,
        rerank_threshold: float = 0.0,      # Low-confidence Filtering
        max_tokens: Optional[int] = None,   # Token Budget Strategy (defaults to settings.GROUNDING_TOKEN_BUDGET)
        document_ids: Optional[List[UUID]] = None,  # P1: per-chat isolation
    ) -> Dict[str, Any]:
        """
        Orchestrates the pipeline from semantic retrieval -> reranking -> formatting.
        Produces deterministic, citation-ready contexts for the LLM.

        P1: when ``document_ids`` is provided, retrieval is restricted to only
        those documents (in addition to the workspace + owner filters
        downstream). Callers in /query/stream pass the document_ids attached
        to the current chat session so other chats' docs don't bleed in.
        """
        start_time = time.time()

        # PHASE 2: pick up the configured budget if the caller didn't override.
        if max_tokens is None:
            max_tokens = getattr(settings, "GROUNDING_TOKEN_BUDGET", 4000)

        # P1: empty document_ids list is meaningful — it means "this chat has
        # no attached docs", in which case retrieval would return nothing
        # anyway. Short-circuit to skip the (unnecessarily wide) DB call.
        if document_ids is not None and len(document_ids) == 0:
            return {
                "query": query,
                "grounded_context_str": "",
                "evidence_metadata": [],
                "confidence_score": 0.0,
                "tracing": {
                    "retrieval_tracing": {
                        "embedding_time_sec": 0.0,
                        "database_time_sec": 0.0,
                        "total_time_sec": 0.0,
                    },
                    "reranking_time_sec": 0.0,
                    "total_grounding_time_sec": round(time.time() - start_time, 4),
                    "candidates_retrieved": 0,
                    "evidence_accepted": 0,
                    "estimated_tokens": 0,
                },
            }

        # 1. Candidate Retrieval (Top-30 Expansion Strategy)
        # We fetch a wide net from pgvector because vector search is highly scalable
        # but misses fine-grained cross-attention semantic nuance.
        retrieval_payload = await RetrievalService.retrieve_chunks(
            db=db,
            query=query,
            workspace_id=workspace_id,
            top_k=retrieval_top_k,
            similarity_threshold=similarity_threshold,
            document_ids=document_ids,  # P1: forward chat-scoped filter
        )
        candidates = retrieval_payload["results"]
        
        # 2. Duplicate Chunk Suppression
        seen_chunks = set()
        unique_candidates = []
        for c in candidates:
            if c["chunk_id"] not in seen_chunks:
                seen_chunks.add(c["chunk_id"])
                unique_candidates.append(c)
                
        # 3. Reranking Orchestration
        rerank_start = time.time()
        reranked_candidates = reranker_service.rerank_results(query, unique_candidates)
        rerank_duration = time.time() - rerank_start
        
        # 4. Low-Confidence Filtering & Top-N Selection
        filtered_candidates = [c for c in reranked_candidates if c["rerank_score"] >= rerank_threshold]
        selected_candidates = filtered_candidates[:final_top_k]

        # PHASE 2: present chunks to the LLM IN DOCUMENT ORDER so it can
        # reason linearly across the doc and produce page-ordered citations.
        # Sort key: (filename, page_number, chunk_index). This is purely a
        # presentation reorder — the rerank_score is preserved for scoring.
        selected_candidates = sorted(
            selected_candidates,
            key=lambda c: (
                str(c.get("filename") or ""),
                int(c.get("page_number") or 0),
                int(c.get("chunk_index") or 0),
            ),
        )

        # 5. Token Budgeting & Grounded Context Formatting
        grounded_context = []
        current_token_estimate = 0
        accepted_evidence = []

        for candidate in selected_candidates:
            # Heuristic: ~4 characters per token
            chunk_tokens = len(candidate["text_content"]) // 4 
            if current_token_estimate + chunk_tokens > max_tokens:
                logger.warning(f"[Tracing] Token budget exceeded ({max_tokens}). Halting evidence injection.")
                break
                
            current_token_estimate += chunk_tokens
            accepted_evidence.append(candidate)
            
            # Citation formatting natively prepares the LLM to output grounded references
            context_block = (
                f"<evidence document=\"{candidate['filename']}\" "
                f"page=\"{candidate['page_number']}\" "
                f"chunk_id=\"{candidate['chunk_id']}\">\n"
                f"{candidate['text_content']}\n"
                f"</evidence>"
            )
            grounded_context.append(context_block)
            
        total_duration = time.time() - start_time
        
        # 6. Confidence Score Strategy
        # Average of top accepted rerank scores serves as a "hallucination risk" metric
        confidence_score = 0.0
        if accepted_evidence:
            confidence_score = round(sum(c["rerank_score"] for c in accepted_evidence) / len(accepted_evidence), 4)
            
        return {
            "query": query,
            "grounded_context_str": "\n\n".join(grounded_context),
            "evidence_metadata": accepted_evidence,
            "confidence_score": confidence_score,
            "tracing": {
                "retrieval_tracing": retrieval_payload["tracing"],
                "reranking_time_sec": round(rerank_duration, 4),
                "total_grounding_time_sec": round(total_duration, 4),
                "candidates_retrieved": len(candidates),
                "evidence_accepted": len(accepted_evidence),
                "estimated_tokens": current_token_estimate
            }
        }
