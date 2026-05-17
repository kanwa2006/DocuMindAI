import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any
import json
import asyncio

from app.db.session import get_db
from app.schemas.query import QueryRequest, QueryResponse, EvidenceChunk, TracingDiagnostics
from app.services.grounding_service import GroundingService
from app.services.llm_service import llm_service
from app.services.retrieval_service import RetrievalService
from app.core.auth import get_current_user
import uuid

router = APIRouter()

@router.post("/search", response_model=QueryResponse)
async def semantic_search(
    request: QueryRequest, 
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Pure semantic search endpoint. Protected by tenant isolation."""
    payload = await RetrievalService.retrieve_chunks(
        db=db,
        query=request.query,
        workspace_id=uuid.UUID(current_user["workspace_id"]),
        top_k=request.top_k,
        similarity_threshold=request.similarity_threshold
    )
    
    evidence = [EvidenceChunk(**c) for c in payload["results"]]
    
    diagnostics = TracingDiagnostics(
        embedding_time_sec=payload["tracing"]["embedding_time_sec"],
        database_time_sec=payload["tracing"]["database_time_sec"],
        total_time_sec=payload["tracing"]["total_time_sec"]
    )
    
    return QueryResponse(
        query=request.query,
        answer="[Search Only - Generation Bypassed]",
        confidence_score=1.0,
        evidence=evidence,
        diagnostics=diagnostics
    )

@router.post("/ask", response_model=QueryResponse)
async def ask_question(
    request: QueryRequest, 
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Full orchestration. Workspace strictly enforced by JWT auth."""
    grounding_payload = await GroundingService.prepare_grounded_context(
        db=db,
        query=request.query,
        workspace_id=uuid.UUID(current_user["workspace_id"]),
        final_top_k=request.top_k,
        similarity_threshold=request.similarity_threshold
    )
    
    generation_payload = await llm_service.generate_answer(
        query=request.query,
        grounded_context=grounding_payload["grounded_context_str"]
    )
    
    evidence = [EvidenceChunk(**c) for c in grounding_payload["evidence_metadata"]]
    tracing = grounding_payload["tracing"]
    total_time = tracing["total_grounding_time_sec"] + generation_payload["generation_time_sec"]
    
    diagnostics = TracingDiagnostics(
        embedding_time_sec=tracing["retrieval_tracing"]["embedding_time_sec"],
        database_time_sec=tracing["retrieval_tracing"]["database_time_sec"],
        reranking_time_sec=tracing["reranking_time_sec"],
        generation_time_sec=generation_payload["generation_time_sec"],
        total_time_sec=round(total_time, 4),
        candidates_retrieved=tracing["candidates_retrieved"],
        evidence_accepted=tracing["evidence_accepted"],
        estimated_tokens=tracing["estimated_tokens"]
    )
    
    return QueryResponse(
        query=request.query,
        answer=generation_payload["answer"],
        confidence_score=grounding_payload["confidence_score"],
        evidence=evidence,
        diagnostics=diagnostics
    )

@router.post("/stream")
async def ask_question_stream(
    request: QueryRequest, 
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """SSE endpoint for live incremental token streaming and progress events."""
    async def event_generator():
        try:
            # 1. Retrieval Phase Event
            yield f"event: status\ndata: {json.dumps({'message': 'Retrieving semantic chunks...'})}\n\n"
            
            grounding_payload = await GroundingService.prepare_grounded_context(
                db=db,
                query=request.query,
                workspace_id=uuid.UUID(current_user["workspace_id"]),
                final_top_k=request.top_k,
                similarity_threshold=request.similarity_threshold
            )
            
            # Send metadata immediately so frontend renders citations before generation finishes
            metadata = {
                "confidence_score": grounding_payload["confidence_score"],
                "evidence": grounding_payload["evidence_metadata"],
                "tracing": grounding_payload["tracing"]
            }
            yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"
            
            grounded_context = grounding_payload["grounded_context_str"]
            if not grounded_context.strip():
                yield f"event: token\ndata: {json.dumps({'token': 'I do not have sufficient evidence in your documents to answer this question.'})}\n\n"
            else:
                yield f"event: status\ndata: {json.dumps({'message': 'Generating grounded response...'})}\n\n"
                system_prompt = llm_service._build_system_prompt(grounded_context)
                user_prompt = f"Question: {request.query}"
                
                async for token in llm_service.provider.generate_stream(system_prompt, user_prompt):
                    yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
                    # Micro-sleep allows ASGI to check for client disconnects
                    await asyncio.sleep(0.005)
                    
            yield f"event: done\ndata: {{}}\n\n"
            
        except asyncio.CancelledError:
            # Graceful cancellation if client drops
            raise
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/debug", response_model=QueryResponse)
async def debug_retrieval(
    request: QueryRequest, 
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Exposes deep trace metadata for prompt and relevance debugging."""
    return await ask_question(request, current_user, db)
