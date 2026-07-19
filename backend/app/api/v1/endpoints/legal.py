from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Any, Optional
import uuid
import asyncio
import re
import json
import time
import logging
from datetime import datetime, timezone

from pydantic import BaseModel

from app.db.session import get_db
from app.core.auth import get_current_user
from app.core.workspace import resolve_workspace_id
from app.models.legal import Contract, Clause, ComplianceRule, RedlineSuggestion, ApprovalWorkflow
from app.models.legal_analysis import LegalAnalysis, LegalAuditLog
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.schemas.legal import (
    ContractResponse, ComplianceRuleCreate, ComplianceRuleResponse,
    ContractSegmentationSchema, ClauseComplianceSchema,
)
from app.services.llm_service import llm_service
from app.workers.tasks.legal_tasks import process_contract_batch

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Task 6-L1: Mandatory legal disclaimer ─────────────────────────────────────

LEGAL_DISCLAIMER = (
    "⚠ This analysis is AI-generated for informational purposes only. "
    "It does not constitute legal advice. Always consult a qualified legal professional."
)

# ── Risk level ordering (Task 6-L4) ──────────────────────────────────────────

RISK_LEVELS = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3, "Unassessable": -1}

# ── Request schemas ───────────────────────────────────────────────────────────

class ContractCompareRequest(BaseModel):
    doc_id_a: str
    doc_id_b: str
    label_a: str = "Document A"
    label_b: str = "Document B"

# ── Helper: fetch and join document chunks ────────────────────────────────────

async def _get_document_text(db: AsyncSession, document_id: uuid.UUID) -> str:
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = result.scalars().all()
    return "\n".join(c.text_content for c in chunks)


# ── Helper: log immutable audit event ─────────────────────────────────────────

async def _log_audit(
    db: AsyncSession,
    user_id: Optional[uuid.UUID],
    document_id: Optional[uuid.UUID],
    analysis_id: Optional[uuid.UUID],
    event_type: str,
    event_detail: dict = None,
):
    """Insert-only audit log entry. Never log document content or PII."""
    try:
        entry = LegalAuditLog(
            user_id=user_id,
            document_id=document_id,
            analysis_id=analysis_id,
            event_type=event_type,
            event_detail=event_detail or {},
        )
        db.add(entry)
        await db.commit()
    except Exception as exc:
        logger.warning(f"[legal/audit_log] Failed to write audit entry: {exc}")

@router.post("/rules", response_model=ComplianceRuleResponse)
async def create_compliance_rule(
    request: ComplianceRuleCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    rule = ComplianceRule(
        workspace_id=workspace_id,
        name=request.name,
        category=request.category,
        rule_description=request.rule_description,
        mandatory=request.mandatory
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule

@router.get("/rules", response_model=List[ComplianceRuleResponse])
async def list_rules(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    result = await db.execute(select(ComplianceRule).where(ComplianceRule.workspace_id == workspace_id))
    return result.scalars().all()

@router.post("/contracts/process")
async def process_contract(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 1: ASYNC LEGAL PROCESSING
    Offloads heavy compliance processing to Celery workers.
    """
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    doc = (await db.execute(select(Document).where(Document.id == document_id, Document.workspace_id == workspace_id))).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Dispatch to Celery
    process_contract_batch.delay(str(document_id), str(workspace_id))
    
    return {"status": "processing_queued", "document_id": str(document_id)}

@router.get("/events/legal/{document_id}")
async def sse_legal_processing_updates(
    document_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    PHASE 1: Live Processing Updates
    Server-Sent Events (SSE) endpoint to push contract processing status.
    """
    # M-1: real Document.status transitions instead of a fake heartbeat.
    from app.services.processing_events import document_status_event_stream
    return StreamingResponse(
        document_status_event_stream(document_id, current_user["id"]),
        media_type="text/event-stream",
    )

@router.get("/clauses/search")
async def semantic_search_clauses(
    query: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 2: LEGAL VECTOR SEARCH
    Uses pgvector to perform semantic similarity search across historical clauses.
    """
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    
    # Generate query embedding
    query_embedding = await llm_service.get_embedding(query)
    
    # Search closest clauses via <-> L2 distance
    stmt = (
        select(Clause, Contract)
        .join(Contract, Clause.contract_id == Contract.id)
        .where(Clause.workspace_id == workspace_id)
        .order_by(Clause.embedding.l2_distance(query_embedding))
        .limit(10)
    )
    result = await db.execute(stmt)
    
    matches = []
    for clause, contract in result.all():
        matches.append({
            "contract_title": contract.title,
            "section_name": clause.section_name,
            "original_text": clause.original_text,
            "clause_type": clause.clause_type,
            "risk_level": clause.risk_level
        })
    return matches

@router.post("/contracts/{contract_id}/approvals")
async def add_contract_approval(
    contract_id: uuid.UUID,
    status: str,
    comments: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 4: LEGAL COLLABORATION
    Adds an approval or rejection decision to the contract's audit timeline.
    """
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    reviewer_id = uuid.UUID(current_user["id"])
    
    approval = ApprovalWorkflow(
        workspace_id=workspace_id,
        contract_id=contract_id,
        reviewer_id=reviewer_id,
        status=status,
        comments=comments
    )
    db.add(approval)
    
    contract = (await db.execute(select(Contract).where(Contract.id == contract_id))).scalar_one_or_none()
    if contract:
        contract.status = status
        
    await db.commit()
    return {"status": "success"}

@router.get("/contracts", response_model=List[ContractResponse])
async def list_contracts(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    result = await db.execute(select(Contract).where(Contract.workspace_id == workspace_id).order_by(Contract.created_at.desc()))
    return result.scalars().all()

@router.get("/contracts/{contract_id}/clauses")
async def get_contract_clauses(
    contract_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user["workspace_id"])

    stmt = (
        select(Clause, RedlineSuggestion)
        .outerjoin(RedlineSuggestion, Clause.id == RedlineSuggestion.clause_id)
        .where(Clause.contract_id == contract_id, Clause.workspace_id == workspace_id)
        .order_by(Clause.created_at.asc())
    )
    result = await db.execute(stmt)

    clauses_dict = {}
    for clause, redline in result.all():
        if clause.id not in clauses_dict:
            clauses_dict[clause.id] = {
                "clause": clause,
                "redlines": []
            }
        if redline:
            clauses_dict[clause.id]["redlines"].append(redline)

    return list(clauses_dict.values())


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 6-L — NEW ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

# NOTE: /contracts/compare must be defined BEFORE /contracts/{id}/risk-report
# to prevent FastAPI matching "compare" as a UUID path parameter.

@router.post("/contracts/compare")
async def compare_contracts(
    request: ContractCompareRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Task 6-L7: Compare two contracts clause-by-clause.
    Returns matching clauses with differences, and clauses unique to each document.
    """
    doc_a_id = uuid.UUID(request.doc_id_a)
    doc_b_id = uuid.UUID(request.doc_id_b)

    text_a = await _get_document_text(db, doc_a_id)
    text_b = await _get_document_text(db, doc_b_id)

    if not text_a.strip() or not text_b.strip():
        raise HTTPException(status_code=422, detail="One or both documents have no extractable text.")

    system_prompt = (
        "You are a legal document comparison assistant. "
        "Return ONLY a valid JSON object — no prose, no markdown, no explanation. "
        "Compare the two contracts and return:\n"
        "{\n"
        '  "matching_clauses": [\n'
        '    { "clause_type": str, "doc_a": str, "doc_b": str,\n'
        '      "material_difference": bool, "difference_note": str }\n'
        "  ],\n"
        '  "clauses_in_a_only": [ { "clause_type": str, "risk_note": str } ],\n'
        '  "clauses_in_b_only": [ { "clause_type": str, "risk_note": str } ]\n'
        "}"
    )
    user_prompt = (
        f"CONTRACT A ({request.label_a}, first 6000 chars):\n{text_a[:6000]}\n\n"
        f"CONTRACT B ({request.label_b}, first 6000 chars):\n{text_b[:6000]}"
    )

    try:
        raw_llm = await llm_service.generate(system_prompt, user_prompt)
        raw_llm = re.sub(r'^```(?:json)?\s*', '', raw_llm.strip(), flags=re.MULTILINE)
        raw_llm = re.sub(r'```\s*$', '', raw_llm.strip(), flags=re.MULTILINE)
        comparison = json.loads(raw_llm)
    except Exception as exc:
        logger.warning(f"[legal/compare] LLM parse failed: {exc}")
        comparison = {"matching_clauses": [], "clauses_in_a_only": [], "clauses_in_b_only": []}

    comparison["label_a"] = request.label_a
    comparison["label_b"] = request.label_b
    comparison["disclaimer"] = LEGAL_DISCLAIMER
    return comparison


@router.post("/contracts/{contract_id}/risk-report")
async def generate_risk_report(
    contract_id: uuid.UUID,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Tasks 6-L1 + 6-L2 + 6-L3 + 6-L4 + 6-L5 + 6-L6:
    Generate a full contract risk report with per-clause confidence scoring,
    consistency validation against previous analyses, escalation logic, and audit trail.
    Mandatory legal disclaimer prepended to every response.
    """
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    user_id_str = current_user.get("id")
    user_id = uuid.UUID(user_id_str) if user_id_str else None
    client_ip = request.client.host if request.client else "unknown"
    t_start = time.time()

    # Resolve contract → document
    contract = (await db.execute(
        select(Contract).where(Contract.id == contract_id, Contract.workspace_id == workspace_id)
    )).scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")

    doc_id = contract.document_id
    doc_text = await _get_document_text(db, uuid.UUID(str(doc_id)))
    if not doc_text.strip():
        raise HTTPException(status_code=422, detail="Contract document has no extractable text.")

    # LLM generates structured risk JSON (Tasks 6-L2 + 6-L3)
    system_prompt = (
        "You are a legal risk assessment assistant. "
        "Return ONLY a valid JSON object — no prose, no markdown, no explanation. "
        "Analyze the contract and return:\n"
        "{\n"
        '  "overall_risk_score": int (0-100),\n'
        '  "overall_risk_level": "Low"|"Medium"|"High"|"Critical",\n'
        '  "summary": str,\n'
        '  "clause_risks": [\n'
        '    {\n'
        '      "clause_type": str,\n'
        '      "text_excerpt": str,\n'
        '      "risk_level": "Low"|"Medium"|"High"|"Critical",\n'
        '      "risk_reason": str,\n'
        '      "confidence_score": float (0.0-1.0),\n'
        '      "confidence_basis": "clause_clearly_stated"|"inferred_from_context"'
        '|"ambiguous_language"|"insufficient_text",\n'
        '      "page": int|null,\n'
        '      "recommendation": str\n'
        '    }\n'
        '  ],\n'
        '  "missing_clauses": [str]\n'
        "}\n\n"
        "CRITICAL RULE: If confidence_basis == 'insufficient_text' OR confidence_score < 0.50, "
        "set risk_level to 'Unassessable' and begin risk_reason with "
        "'Insufficient information to assess...'. "
        "Risk colors: Critical=red, High=orange, Medium=amber, Low=green."
    )
    user_prompt = f"Contract text (first 10000 chars):\n{doc_text[:10000]}"

    try:
        raw_llm = await llm_service.generate(system_prompt, user_prompt)
        raw_llm = re.sub(r'^```(?:json)?\s*', '', raw_llm.strip(), flags=re.MULTILINE)
        raw_llm = re.sub(r'```\s*$', '', raw_llm.strip(), flags=re.MULTILINE)
        risk_data = json.loads(raw_llm)
    except Exception as exc:
        logger.warning(f"[legal/risk-report] LLM parse failed: {exc}")
        risk_data = {
            "overall_risk_score": 0,
            "overall_risk_level": "Low",
            "summary": "Unable to parse risk analysis.",
            "clause_risks": [],
            "missing_clauses": [],
        }

    clause_risks = risk_data.get("clause_risks", [])
    missing_clauses = risk_data.get("missing_clauses", [])
    overall_score = risk_data.get("overall_risk_score", 0)
    overall_level = risk_data.get("overall_risk_level", "Low")

    # Task 6-L4: Consistency validation against previous analysis
    prev_analysis = (await db.execute(
        select(LegalAnalysis)
        .where(LegalAnalysis.document_id == doc_id)
        .order_by(LegalAnalysis.created_at.desc())
    )).scalar_one_or_none()

    consistency_warnings = []
    if prev_analysis and prev_analysis.clause_risks:
        prev_map = {
            c["clause_type"]: c.get("risk_level")
            for c in prev_analysis.clause_risks
            if isinstance(c, dict) and c.get("clause_type")
        }
        for clause in clause_risks:
            ct = clause.get("clause_type", "")
            new_level = clause.get("risk_level", "")
            old_level = prev_map.get(ct)
            if old_level and old_level in RISK_LEVELS and new_level in RISK_LEVELS:
                if RISK_LEVELS[new_level] >= 0 and RISK_LEVELS[old_level] >= 0:
                    diff = abs(RISK_LEVELS[new_level] - RISK_LEVELS[old_level])
                    if diff >= 2:
                        consistency_warnings.append({
                            "clause_type": ct,
                            "previous_level": old_level,
                            "current_level": new_level,
                            "warning": (
                                f"Risk level changed significantly from previous analysis. "
                                "Manual review recommended."
                            ),
                        })

    # Task 6-L5: Escalation triggers — Python logic, not LLM
    escalation_required = False
    escalation_reason = None
    if overall_score >= 70:
        escalation_required = True
        escalation_reason = "Overall contract risk score is High or Critical."
    elif any(c.get("risk_level") == "Critical" for c in clause_risks):
        escalation_required = True
        escalation_reason = "One or more Critical risk clauses identified."
    elif len(missing_clauses) >= 3:
        escalation_required = True
        escalation_reason = "Three or more standard clauses are missing."

    elapsed_ms = int((time.time() - t_start) * 1000)

    # Task 6-L6: Persist analysis record
    analysis = LegalAnalysis(
        workspace_id=workspace_id,
        document_id=doc_id,
        contract_id=contract_id,
        user_id=user_id,
        overall_risk_score=overall_score,
        overall_risk_level=overall_level,
        summary=risk_data.get("summary", ""),
        clause_risks=clause_risks,
        missing_clauses=missing_clauses,
        consistency_warnings=consistency_warnings,
        escalation_required=escalation_required,
        escalation_reason=escalation_reason,
        model_version="gemini",
        analysis_version="v1.0",
        ip_address=client_ip,
        request_timestamp=datetime.now(timezone.utc),
        response_duration_ms=elapsed_ms,
        clause_count=len(clause_risks),
        missing_clause_count=len(missing_clauses),
    )
    try:
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)
    except Exception as exc:
        logger.warning(f"[legal/risk-report] Analysis persistence failed: {exc}")
        await db.rollback()

    # Immutable audit log — Task 6-L6
    await _log_audit(
        db, user_id, uuid.UUID(str(doc_id)), analysis.id,
        "analysis_created",
        {"contract_id": str(contract_id), "overall_risk_score": overall_score},
    )
    if escalation_required:
        await _log_audit(
            db, user_id, uuid.UUID(str(doc_id)), analysis.id,
            "escalation_triggered",
            {"reason": escalation_reason},
        )

    # Task 6-L1: Mandatory disclaimer prepended to every response
    return {
        "disclaimer": LEGAL_DISCLAIMER,
        "overall_risk_score": overall_score,
        "overall_risk_level": overall_level,
        "summary": risk_data.get("summary", ""),
        "clause_risks": clause_risks,
        "missing_clauses": missing_clauses,
        "consistency_warnings": consistency_warnings,
        "escalation_required": escalation_required,
        "escalation_reason": escalation_reason,
        "analysis_id": str(analysis.id) if analysis.id else None,
        "contract_id": str(contract_id),
        "document_id": str(doc_id),
    }


@router.get("/audit-log")
async def get_audit_log(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Task 6-L6: Retrieve current user's audit log (own records only).
    Returns all events ordered by timestamp desc.
    """
    user_id_str = current_user.get("id")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="User ID not found in token.")
    user_id = uuid.UUID(user_id_str)

    result = await db.execute(
        select(LegalAuditLog)
        .where(LegalAuditLog.user_id == user_id)
        .order_by(LegalAuditLog.timestamp.desc())
        .limit(200)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "event_type": log.event_type,
            "document_id": str(log.document_id) if log.document_id else None,
            "analysis_id": str(log.analysis_id) if log.analysis_id else None,
            "event_detail": log.event_detail,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in logs
    ]
