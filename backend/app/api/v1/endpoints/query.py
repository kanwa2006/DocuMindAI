import time
import hashlib
import json as json_module
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Any
import json
import asyncio

from app.db.session import get_db
from app.schemas.query import QueryRequest, QueryResponse, EvidenceChunk, TracingDiagnostics
from app.services.grounding_service import GroundingService
from app.services.llm_service import llm_service
from app.services.retrieval_service import RetrievalService
from app.models.chat import ChatMessage
from app.models.org import User
from app.core.auth import get_current_user
from app.core.workspace import resolve_workspace_id
from app.core.config import settings
from app.core.trial_enforcement import check_and_increment_trial
from app.services.response_schemas import get_response_schema
from app.services.language_detector import detect_query_language, get_language_instruction
from app.services.email_service import send_trial_nudge_email, send_upgrade_reminder_email
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()

# Task 4.7 — mandatory workspace disclaimers (backend appends as final SSE chunk)
WORKSPACE_DISCLAIMERS = {
    "legal": (
        "\n\n---\n"
        "⚠️ **Legal Disclaimer**: This analysis is AI-generated for "
        "informational purposes only. It does not constitute legal advice. "
        "Always consult a qualified legal professional before acting on "
        "any information above."
    ),
    "finance": (
        "\n\n---\n"
        "⚠️ **Financial Disclaimer**: All figures are AI-extracted. "
        "Verify all numbers against original source documents before "
        "any financial, tax, or legal use."
    ),
}


# ── Redis helpers (Task 4.9) — failures are silently ignored, never break request ──

async def _get_cached_retrieval(cache_key: str) -> Any:
    try:
        import aioredis
        redis = await aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        cached = await redis.get(cache_key)
        await redis.close()
        if cached:
            return json_module.loads(cached)
    except Exception:
        pass
    return None


async def _set_cached_retrieval(cache_key: str, payload: Any, ttl: int = 300) -> None:
    try:
        import aioredis
        redis = await aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await redis.setex(cache_key, ttl, json_module.dumps(payload, default=str))
        await redis.close()
    except Exception:
        pass


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
        workspace_id=resolve_workspace_id(current_user["workspace_id"]),
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
        workspace_id=resolve_workspace_id(current_user["workspace_id"]),
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
            # Phase 10 — email verification gate
            user_id = str(current_user["id"])
            user_row = await db.execute(select(User).where(User.id == user_id))
            user_obj = user_row.scalar_one_or_none()
            if user_obj and not user_obj.email_verified:
                yield f"event: error\ndata: {json.dumps({'detail': 'email_not_verified', 'message': 'Please verify your email first.'})}\n\n"
                return

            # Phase 10 — trial quota check (raises HTTP 402 if exhausted)
            trial_status = await check_and_increment_trial(user_id=user_id, db=db)

            # Emit trial_status as first SSE event so frontend can update counter
            if trial_status["plan"] == "trial":
                yield (
                    f"event: trial_status\n"
                    f"data: {json.dumps({'queries_used': trial_status['queries_used'], 'queries_remaining': trial_status['queries_remaining']})}\n\n"
                )
                # Fire-and-forget lifecycle emails — never blocks the stream
                if user_obj and getattr(user_obj, "email_notifications_enabled", True):
                    _loop = asyncio.get_event_loop()
                    _q_used = trial_status["queries_used"]
                    if _q_used == 3:
                        _loop.run_in_executor(
                            None, send_trial_nudge_email,
                            user_obj.email, user_obj.full_name, 3,
                        )
                    elif _q_used == 4:
                        _loop.run_in_executor(
                            None, send_upgrade_reminder_email,
                            user_obj.email, user_obj.full_name,
                        )

            workspace_type = (request.workspace_type or "general").lower().strip()

            # Phase 14.10 — Stage 1: searching
            yield (
                f"event: thinking_stage\n"
                f"data: {json.dumps({'stage': 'searching', 'detail': 'Searching your documents...'})}\n\n"
            )

            # Task 4.8 — workspace-specific retrieval config
            ws_config = settings.WORKSPACE_RETRIEVAL_CONFIG.get(
                workspace_type, settings.WORKSPACE_RETRIEVAL_CONFIG["general"]
            )
            effective_top_k = request.top_k if request.top_k != 5 else ws_config["top_k"]

            # Task 4.3 — fetch last 8 messages for conversation history
            conversation_history = []
            if request.session_id:
                try:
                    sess_uuid = uuid.UUID(request.session_id)
                    stmt = (
                        select(ChatMessage)
                        .where(ChatMessage.session_id == sess_uuid)
                        .order_by(ChatMessage.created_at.desc())
                        .limit(8)
                    )
                    result = await db.execute(stmt)
                    recent_messages = list(reversed(result.scalars().all()))
                    conversation_history = [
                        {"role": msg.role, "content": msg.content}
                        for msg in recent_messages
                        if msg.role in ("user", "assistant")
                    ]
                    logger.info(
                        f"[query/stream] Loaded {len(conversation_history)} history messages "
                        f"for session {request.session_id}"
                    )
                except Exception as exc:
                    logger.warning(f"[query/stream] Failed to load history: {exc}")

            history_text = "\n".join([
                f"{m['role'].upper()}: {m['content'][:300]}"
                for m in conversation_history[-6:]
            ])

            # Task 4.9 — Redis retrieval cache key
            doc_ids_str = str(current_user.get("workspace_id", ""))
            query_hash = hashlib.sha256(
                f"{workspace_type}:{request.query}:{doc_ids_str}".encode()
            ).hexdigest()[:16]
            cache_key = f"retrieval:{workspace_type}:{query_hash}"

            # 1. Retrieval phase
            yield f"event: status\ndata: {json.dumps({'message': 'Retrieving semantic chunks...'})}\n\n"

            grounding_payload = await _get_cached_retrieval(cache_key)
            if grounding_payload:
                logger.info(f"[query/stream] Cache hit: {cache_key}")
            else:
                grounding_payload = await GroundingService.prepare_grounded_context(
                    db=db,
                    query=request.query,
                    workspace_id=resolve_workspace_id(current_user["workspace_id"]),
                    final_top_k=effective_top_k,
                    similarity_threshold=request.similarity_threshold
                )
                await _set_cached_retrieval(cache_key, grounding_payload)

            # Phase 14.10 — Stage 2: reranking
            evidence_count = len(grounding_payload.get("evidence_metadata", []))
            yield (
                f"event: thinking_stage\n"
                f"data: {json.dumps({'stage': 'reranking', 'detail': f'Reviewing {evidence_count} relevant passages...'})}\n\n"
            )

            grounded_context = grounding_payload["grounded_context_str"]
            is_grounded = bool(grounded_context.strip())

            # Send metadata immediately so frontend renders citations before generation finishes.
            # `grounded` / `mode` lets the UI show an "Ungrounded" badge instead of a fake TrustScore.
            metadata = {
                "confidence_score": grounding_payload["confidence_score"] if is_grounded else 0.0,
                "evidence": grounding_payload["evidence_metadata"] if is_grounded else [],
                "tracing": grounding_payload["tracing"],
                "grounded": is_grounded,
                "mode": "grounded" if is_grounded else "general",
            }
            yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"

            yield f"event: status\ndata: {json.dumps({'message': 'Generating grounded response...' if is_grounded else 'Generating response from workspace context...'})}\n\n"

            # Phase 14.10 — Stage 3: generating
            yield (
                f"event: thinking_stage\n"
                f"data: {json.dumps({'stage': 'generating', 'detail': 'Generating response...'})}\n\n"
            )

            # C10 — no-document mode: skip grounded prompt; answer from workspace system prompt only.
            if is_grounded:
                system_prompt = llm_service._build_system_prompt(grounded_context)
            else:
                system_prompt = (
                    "You are DocuMindAI, a helpful assistant. The user has not attached "
                    "any documents to this workspace, so answer from general knowledge. "
                    "Be concise and clear. Never invent citations or quote non-existent "
                    "documents. If the user's question would require document content "
                    "to answer accurately, recommend they upload one for grounded, "
                    "cited responses."
                )

            # Phase 15.2 — inject workspace response schema
            schema = get_response_schema(workspace_type)
            system_prompt = f"{system_prompt}\n\n{schema}"

            # Phase 15.4 — inject language instruction
            preferred_lang = (
                getattr(user_obj, "preferred_language", "auto") or "auto"
            )
            if preferred_lang != "auto":
                query_language = preferred_lang
            else:
                query_language = detect_query_language(request.query)
            lang_instruction = get_language_instruction(query_language)
            if lang_instruction:
                system_prompt = system_prompt + lang_instruction

            # Phase 14.6 — comparison mode: augment system prompt
            if is_grounded and getattr(request, "comparison_mode", False):
                system_prompt = system_prompt + (
                    "\n\nCOMPARISON MODE ACTIVE: You are comparing multiple documents. "
                    "For each point, specify which document supports it using [Doc A], [Doc B] notation. "
                    "Format your response as a structured comparison. "
                    "Use a table when 3 or more dimensions are compared."
                )

            # Task 4.3 — prepend conversation history to user prompt
            if history_text:
                user_prompt = (
                    f"Previous conversation:\n{history_text}\n\n---\n\n"
                    f"Question: {request.query}"
                )
            else:
                user_prompt = f"Question: {request.query}"

            async for token in llm_service.provider.generate_stream(system_prompt, user_prompt):
                yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
                # Micro-sleep allows ASGI to check for client disconnects
                await asyncio.sleep(0.005)

            # Task 4.7 — append workspace disclaimer (legal/finance only — keeps regulatory
            # voice in no-doc mode where users might still ask domain questions).
            disclaimer = WORKSPACE_DISCLAIMERS.get(workspace_type, "")
            if disclaimer:
                yield f"event: token\ndata: {json.dumps({'token': disclaimer})}\n\n"

            yield f"event: done\ndata: {{}}\n\n"

        except asyncio.CancelledError:
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
