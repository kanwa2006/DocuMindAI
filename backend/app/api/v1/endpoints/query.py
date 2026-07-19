import time
import hashlib
import json as json_module
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Any, Dict
import json
import asyncio

from app.db.session import get_db
from app.schemas.query import QueryRequest, QueryResponse, EvidenceChunk, TracingDiagnostics
from app.services.grounding_service import GroundingService
from app.services.llm_service import llm_service
from app.services.retrieval_service import RetrievalService
from app.services.summary_service import (
    is_summary_intent,
    generate_full_document_summary_stream,
)
from app.models.chat import ChatMessage
from app.models.document import Document, DocumentStatus
from app.models.org import User
from app.core.auth import get_current_user
from app.core.workspace import resolve_workspace_id
from app.core.config import settings
from app.core.trial_enforcement import check_and_increment_trial, TRIAL_QUERY_LIMIT
from app.services.response_schemas import get_response_schema
from app.services.language_detector import detect_query_language, get_language_instruction
from app.services.email_service import send_trial_nudge_email, send_upgrade_reminder_email
from app.services.veritas_engine import veritas_engine, VeritasEngine, VeritasTrustReport
from app.core.rate_limiter import limiter
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


# ── C-4: Veritas trust report on the main query path ──────────────────────────

def _veritas_sse_payload(report: VeritasTrustReport) -> Dict[str, Any]:
    """Map VeritasTrustReport to the frontend TrustReport interface.

    The SSE consumer contract lives in frontend TrustScoreBadge.tsx
    (final_score, level HIGH|MEDIUM|LOW, evidence_items, warnings,
    factors[{name,weight,score}], contradictions, summary) and differs from
    the backend dataclass field names — adapt here, at the caller, so
    veritas_engine stays untouched (REPAIR_RULEBOOK §8a).
    """
    level = report.grade if report.grade in ("HIGH", "MEDIUM") else "LOW"
    return {
        "final_score": report.final_score,
        "level": level,
        "evidence_items": report.evidence,
        "warnings": report.warnings,
        "factors": [
            {"name": name, "weight": VeritasEngine.WEIGHTS.get(name, 0.0), "score": score}
            for name, score in report.factor_scores.items()
        ],
        "contradictions": [],
        "summary": (
            f"Veritas scored this answer {report.final_score}/100 "
            f"({level}) from {len(report.factor_scores)} weighted factors."
        ),
    }


async def _compute_trust_event(
    answer: str, chunks: Any, query: str, document_ids: Any, db: Any
) -> str:
    """Compute the Veritas report and render the SSE frame.

    Returns "" on failure — the trust event must never break token delivery,
    but the failure is logged at ERROR (no silent degradation)."""
    try:
        dict_chunks = [c for c in (chunks or []) if isinstance(c, dict)]
        report = await veritas_engine.compute_trust_score(
            answer=answer,
            primary_chunks=dict_chunks,
            query=query,
            document_ids=[str(d) for d in document_ids] if document_ids else None,
            db=db,
        )
        return f"event: trust_report\ndata: {json.dumps(_veritas_sse_payload(report))}\n\n"
    except Exception:
        logger.error("[query/stream] Veritas trust computation failed", exc_info=True)
        return ""


def _retrieval_cache_key(user_id: str, workspace_type: str, query: str, attached_doc_ids) -> str:
    """M-2: single source of truth for the retrieval cache key.

    The key MUST start with `retrieval:uid_{user_id}:` — that is the pattern
    `delete_document` purges (documents.py). The old write key
    (`retrieval:{workspace}:{hash}`) never matched the purge pattern, so
    deleted-document content could be served from cache for up to the TTL.
    """
    attached_ids_key = ",".join(sorted(str(d) for d in attached_doc_ids or []))
    digest = hashlib.sha256(
        f"{workspace_type}:{query}:{attached_ids_key}".encode()
    ).hexdigest()[:16]
    return f"retrieval:uid_{user_id}:{workspace_type}:{digest}"


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


# L-6: the duplicate answer surfaces were consolidated. /query/search and
# /query/debug had no consumers (API_AUDIT §2.4) and were removed; two
# answer paths remain with distinct roles:
#   POST /query/stream — the interactive SSE path (trial, cache, Veritas).
#   POST /query/ask    — the synchronous path used by the /chats ask flow
#                        that persists messages.
# Both ground via the same GroundingService + llm_service pipeline.


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
@limiter.limit("30/minute")  # BUG-010 FIX: Prevent runaway LLM cost + DoS
async def ask_question_stream(
    request: Request,
    body: QueryRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """SSE endpoint for live incremental token streaming and progress events."""
    # SlowAPI requires `request: Request` as the first param for IP extraction.
    # The query payload comes via `body: QueryRequest` (FastAPI auto-parses JSON body).
    # All internal references to `request.query`, `request.session_id`, etc. are
    # updated to use `body` below via the event_generator closure.
    request_data = body  # alias used throughout event_generator

    async def event_generator():
        try:
            user_id = str(current_user["id"])
            # Phase 10 email-verification gate removed (deep-debug A1): verification is now
            # optional. Backend may still flip email_verified on /verify-email, but unverified
            # users are not blocked from asking questions.

            # Load the User row once — needed for email-notification preferences and
            # preferred_language. Tolerates a missing row (DummyDB / deleted user) by
            # leaving user_obj as None; downstream getattr() calls fall back to defaults.
            user_obj = None
            try:
                _u_result = await db.execute(
                    select(User).where(User.id == uuid.UUID(user_id))
                )
                user_obj = _u_result.scalar_one_or_none()
            except Exception as _u_exc:
                logger.warning(f"[query/stream] Could not load User {user_id}: {_u_exc}")

            # Phase 10 — trial quota check (raises HTTP 402 if exhausted)
            trial_status = await check_and_increment_trial(user_id=user_id, db=db)

            # Emit trial_status as first SSE event so frontend can update counter
            if trial_status["plan"] == "trial":
                yield (
                    f"event: trial_status\n"
                    f"data: {json.dumps({'queries_used': trial_status['queries_used'], 'queries_remaining': trial_status['queries_remaining']})}\n\n"
                )
                # Fire-and-forget lifecycle emails — never blocks the stream.
                # M-7: thresholds derive from TRIAL_QUERY_LIMIT (nudge with 2
                # queries left, upgrade reminder with 1 left). The old
                # hardcoded 3/4 assumed a 5-query limit; the limit is 10.
                if user_obj and getattr(user_obj, "email_notifications_enabled", True):
                    _loop = asyncio.get_event_loop()
                    _q_used = trial_status["queries_used"]
                    if _q_used == TRIAL_QUERY_LIMIT - 2:
                        _loop.run_in_executor(
                            None, send_trial_nudge_email,
                            user_obj.email, user_obj.full_name, _q_used,
                        )
                    elif _q_used == TRIAL_QUERY_LIMIT - 1:
                        _loop.run_in_executor(
                            None, send_upgrade_reminder_email,
                            user_obj.email, user_obj.full_name,
                        )

            workspace_type = (body.workspace_type or "general").lower().strip()

            # Phase 14.10 — Stage 1: searching
            yield (
                f"event: thinking_stage\n"
                f"data: {json.dumps({'stage': 'searching', 'detail': 'Searching your documents...'})}\n\n"
            )

            # Task 4.8 — workspace-specific retrieval config
            ws_config = settings.WORKSPACE_RETRIEVAL_CONFIG.get(
                workspace_type, settings.WORKSPACE_RETRIEVAL_CONFIG["general"]
            )
            effective_top_k = body.top_k if body.top_k != 5 else ws_config["top_k"]

            # Task 4.3 — fetch last 8 messages for conversation history
            # P1 — also fetch the documents attached to THIS chat session so
            # retrieval can be scoped to them only.
            conversation_history = []
            attached_doc_ids: list = []  # P1: doc UUIDs for this chat only
            owner_uuid = uuid.UUID(user_id)
            if body.session_id:
                try:
                    sess_uuid = uuid.UUID(body.session_id)
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
                        f"for session {body.session_id}"
                    )

                    # P1: docs attached to this exact chat, READY only.
                    # Owner filter is belt-and-suspenders on top of the
                    # session_id (which is owned by the user already, but
                    # the joint filter prevents any cross-tenant leak if
                    # the session_id is ever spoofed).
                    doc_stmt = (
                        select(Document.id)
                        .where(Document.chat_session_id == sess_uuid)
                        .where(Document.owner_id == owner_uuid)
                        .where(Document.status == DocumentStatus.READY)
                    )
                    doc_result = await db.execute(doc_stmt)
                    attached_doc_ids = [row[0] for row in doc_result.all()]
                    logger.info(
                        f"[query/stream] Chat {body.session_id} has "
                        f"{len(attached_doc_ids)} attached READY docs"
                    )
                except Exception as exc:
                    logger.warning(f"[query/stream] Failed to load history/docs: {exc}")

            # PART 4 — strengthen conversation context.
            # Old behaviour truncated to 300 chars per message AND fed raw
            # assistant-side JSON (the streaming response is JSON-serialised
            # before being saved), so the LLM saw `{"answer":"…","evidence":…}`
            # instead of readable text. Both hurt follow-ups like "generate as
            # I mentioned." Fix: extract `.answer` from assistant JSON when
            # parseable, and widen truncation per role.
            def _format_history_message(m: Dict[str, str]) -> str:
                role = m["role"].upper()
                content = m["content"] or ""
                if m["role"] == "assistant":
                    try:
                        parsed = json_module.loads(content)
                        if isinstance(parsed, dict) and "answer" in parsed:
                            content = str(parsed.get("answer") or "")
                    except (ValueError, TypeError):
                        pass
                    return f"{role}: {content[:800]}"
                return f"{role}: {content[:600]}"

            history_text = "\n".join(
                _format_history_message(m) for m in conversation_history[-6:]
            )

            # PHASE 2 — map-reduce summary path. When the user is clearly
            # asking for a summary / overview AND there are attached docs,
            # forget the top-K similarity bias and read the WHOLE document
            # via the summary_service. Top-K retrieval cannot summarize a
            # 40-page doc by definition — it only sees ~10% of it. Normal
            # questions still flow through the existing retrieval path.
            if attached_doc_ids and is_summary_intent(body.query):
                logger.info(
                    f"[query/stream] Summary intent detected → map-reduce on "
                    f"{len(attached_doc_ids)} docs"
                )
                yield (
                    f"event: thinking_stage\n"
                    f"data: {json.dumps({'stage': 'reading', 'detail': 'Reading the full document…'})}\n\n"
                )

                # Emit a placeholder metadata event up-front so the frontend
                # renders the "grounded" badge and trust score even before
                # the reduce step kicks in.
                yield (
                    f"event: metadata\n"
                    f"data: {json.dumps({'confidence_score': 0.95, 'evidence': [], 'grounded': True, 'mode': 'grounded', 'tracing': {}})}\n\n"
                )

                # C-4: accumulate the summary answer + evidence so a real
                # Veritas trust_report can be emitted after the stream.
                summary_answer_parts: list = []
                summary_evidence: list = []
                async for frame in generate_full_document_summary_stream(
                    db=db,
                    query=body.query,
                    document_ids=attached_doc_ids,
                    owner_id=owner_uuid,
                    workspace_type=workspace_type,
                ):
                    kind = frame["kind"]
                    if kind == "stage":
                        yield (
                            f"event: thinking_stage\n"
                            f"data: {json.dumps({'stage': frame['data'], 'detail': frame['data']})}\n\n"
                        )
                    elif kind == "evidence":
                        # Replace the placeholder evidence list once we know
                        # which docs were actually read.
                        summary_evidence = frame["data"] or []
                        yield (
                            f"event: metadata\n"
                            f"data: {json.dumps({'confidence_score': 0.95, 'evidence': frame['data'], 'grounded': True, 'mode': 'grounded'})}\n\n"
                        )
                    elif kind == "token":
                        summary_answer_parts.append(frame["data"])
                        yield f"event: token\ndata: {json.dumps({'token': frame['data']})}\n\n"
                        await asyncio.sleep(0.005)
                    elif kind == "done":
                        # Append workspace disclaimer if relevant (legal/finance).
                        disclaimer = WORKSPACE_DISCLAIMERS.get(workspace_type, "")
                        if disclaimer:
                            yield f"event: token\ndata: {json.dumps({'token': disclaimer})}\n\n"
                        trust_frame = await _compute_trust_event(
                            "".join(summary_answer_parts), summary_evidence,
                            body.query, attached_doc_ids, db,
                        )
                        if trust_frame:
                            yield trust_frame
                        yield f"event: done\ndata: {{}}\n\n"
                        return  # Don't fall through to the retrieval path below.

            # Task 4.9 / M-2 — tenant-scoped retrieval cache key (includes the
            # chat's attached doc ids so two chats in the same workspace
            # asking the same question don't share results, and the
            # uid_{user} prefix so delete_document's purge pattern matches).
            cache_key = _retrieval_cache_key(
                current_user["id"], workspace_type, body.query, attached_doc_ids
            )

            # 1. Retrieval phase
            yield f"event: status\ndata: {json.dumps({'message': 'Retrieving semantic chunks...'})}\n\n"

            grounding_payload = await _get_cached_retrieval(cache_key)
            if grounding_payload:
                logger.info(f"[query/stream] Cache hit: {cache_key}")
            else:
                # P1: if the session has attached docs, pass them through so
                # retrieval is restricted to this chat only. If no session_id
                # or no docs are attached, attached_doc_ids stays []; the
                # GroundingService short-circuits to no-document mode (which
                # the existing C10 logic below handles).
                doc_filter = attached_doc_ids if body.session_id else None
                grounding_payload = await GroundingService.prepare_grounded_context(
                    db=db,
                    query=body.query,
                    workspace_id=resolve_workspace_id(current_user["workspace_id"]),
                    final_top_k=effective_top_k,
                    similarity_threshold=body.similarity_threshold,
                    document_ids=doc_filter,
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
                query_language = detect_query_language(body.query)
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
                    f"Question: {body.query}"
                )
            else:
                user_prompt = f"Question: {body.query}"

            # C-4: accumulate the streamed answer for the post-stream Veritas
            # pass without delaying token delivery.
            answer_parts: list = []
            async for token in llm_service.provider.generate_stream(system_prompt, user_prompt):
                answer_parts.append(token)
                yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
                # Micro-sleep allows ASGI to check for client disconnects
                await asyncio.sleep(0.005)

            # Task 4.7 — append workspace disclaimer (legal/finance only — keeps regulatory
            # voice in no-doc mode where users might still ask domain questions).
            disclaimer = WORKSPACE_DISCLAIMERS.get(workspace_type, "")
            if disclaimer:
                yield f"event: token\ndata: {json.dumps({'token': disclaimer})}\n\n"

            # C-4: emit a real Veritas trust_report after tokens, before done.
            # Grounded answers only — scoring a general-knowledge answer with a
            # document-grounding heuristic would fabricate meaning; the UI
            # shows an "Ungrounded" badge in general mode instead.
            if is_grounded:
                trust_frame = await _compute_trust_event(
                    "".join(answer_parts),
                    grounding_payload.get("evidence_metadata", []),
                    body.query, attached_doc_ids, db,
                )
                if trust_frame:
                    yield trust_frame

            yield f"event: done\ndata: {{}}\n\n"

        except asyncio.CancelledError:
            raise
        except Exception as e:
            # L-12: raw exception text can expose internals (DSNs, hosts,
            # stack details). Log the full error server-side; the client gets
            # a generic message.
            logger.error("[query/stream] Stream failed", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'detail': 'An internal error occurred while generating the response. Please retry.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
