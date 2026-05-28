import time
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.services.retrieval_service import RetrievalService
from app.services.grounding_service import GroundingService

class EvaluationService:
    @staticmethod
    def calculate_mrr(retrieved_ids: List[str], expected_ids: List[str]) -> float:
        """
        Mean Reciprocal Rank (MRR). 
        Calculates how high the first relevant document appears in the retrieved list.
        """
        for i, ret_id in enumerate(retrieved_ids):
            if ret_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    @staticmethod
    async def run_benchmark(
        db: AsyncSession, 
        workspace_id: UUID, 
        queries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        results = []
        total_mrr_before = 0.0
        total_mrr_after = 0.0
        total_latency = 0.0
        
        for q in queries:
            query_str = q["query"]
            expected_docs = [str(eid) for eid in q["expected_document_ids"]]
            
            start_time = time.time()
            
            # Phase 1: Pure Semantic Retrieval (Top 30 Base Accuracy)
            base_payload = await RetrievalService.retrieve_chunks(
                db=db, query=query_str, workspace_id=workspace_id, top_k=30
            )
            base_retrieved_docs = [str(chunk["document_id"]) for chunk in base_payload["results"]]
            mrr_before = EvaluationService.calculate_mrr(base_retrieved_docs, expected_docs)
            
            # Phase 2: Reranking & Grounding (Top 5 Precision)
            grounding_payload = await GroundingService.prepare_grounded_context(
                db=db, query=query_str, workspace_id=workspace_id, final_top_k=5
            )
            reranked_docs = [str(chunk["document_id"]) for chunk in grounding_payload["evidence_metadata"]]
            mrr_after = EvaluationService.calculate_mrr(reranked_docs, expected_docs)
            
            latency = time.time() - start_time
            
            results.append({
                "query": query_str,
                "mrr_before": round(mrr_before, 4),
                "mrr_after": round(mrr_after, 4),
                "latency_sec": round(latency, 4),
                "confidence_score": round(grounding_payload["confidence_score"], 4)
            })
            
            total_mrr_before += mrr_before
            total_mrr_after += mrr_after
            total_latency += latency
            
        num_q = len(queries)
        return {
            "mrr_before_rerank": round(total_mrr_before / num_q if num_q else 0, 4),
            "mrr_after_rerank": round(total_mrr_after / num_q if num_q else 0, 4),
            "avg_latency_sec": round(total_latency / num_q if num_q else 0, 4),
            "results": results
        }
