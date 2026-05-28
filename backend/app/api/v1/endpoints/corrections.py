import csv
import io
import uuid
import logging
from datetime import date
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, desc

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.correction import Correction, CorrectionNote
from app.services.feedback_service import (
    submit_correction,
    approve_correction,
    reject_correction,
    escalate_correction,
    add_correction_note,
    get_correction_trends,
)

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_ISSUE_TYPES = {
    "citation_wrong", "answer_incorrect", "missing_info",
    "hallucination", "source_not_found", "other", "positive_verification",
}
VALID_CONFIDENCES = {"certain", "likely", "unsure"}
VALID_STATUSES = {"pending", "approved", "rejected", "escalated"}


def _require_admin(current_user: dict) -> dict:
    roles = current_user.get("roles", [])
    if "admin" not in roles and "super_admin" not in roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ── Schemas ──────────────────────────────────────────────────────────────────

class SubmitCorrectionRequest(BaseModel):
    session_id: Optional[str] = None
    message_id: Optional[str] = None
    workspace_id: str
    issue_type: str
    incorrect_excerpt: Optional[str] = None
    suggested_correction: Optional[str] = None
    citation_id: Optional[str] = None
    reporter_confidence: str = "unsure"

    @field_validator("issue_type")
    @classmethod
    def validate_issue_type(cls, v: str) -> str:
        if v not in VALID_ISSUE_TYPES:
            raise ValueError(f"issue_type must be one of {VALID_ISSUE_TYPES}")
        return v

    @field_validator("reporter_confidence")
    @classmethod
    def validate_confidence(cls, v: str) -> str:
        if v not in VALID_CONFIDENCES:
            raise ValueError(f"reporter_confidence must be one of {VALID_CONFIDENCES}")
        return v


class UpdateCorrectionRequest(BaseModel):
    action: str  # approve | reject | escalate
    note: Optional[str] = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in {"approve", "reject", "escalate"}:
            raise ValueError("action must be approve, reject, or escalate")
        return v


class AddNoteRequest(BaseModel):
    note_text: str


def _serialize_correction(c: Correction) -> dict:
    return {
        "id": str(c.id),
        "user_id": str(c.user_id),
        "session_id": str(c.session_id) if c.session_id else None,
        "message_id": str(c.message_id) if c.message_id else None,
        "workspace_id": c.workspace_id,
        "issue_type": c.issue_type,
        "incorrect_excerpt": c.incorrect_excerpt,
        "suggested_correction": c.suggested_correction,
        "citation_id": c.citation_id,
        "reporter_confidence": c.reporter_confidence,
        "status": c.status,
        "reviewer_id": str(c.reviewer_id) if c.reviewer_id else None,
        "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
        "eval_query_created": c.eval_query_created,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def post_correction(
    body: SubmitCorrectionRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Submit a correction. status starts as 'pending'. Never touches retrieval."""
    data = body.model_dump()
    # Convert string UUIDs to uuid.UUID where FKs expect it
    if data.get("session_id"):
        data["session_id"] = uuid.UUID(data["session_id"])
    if data.get("message_id"):
        data["message_id"] = uuid.UUID(data["message_id"])

    correction = await submit_correction(
        correction_data=data,
        user_id=uuid.UUID(current_user["id"]),
        db=db,
    )
    return _serialize_correction(correction)


@router.get("/my")
async def get_my_corrections(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List the authenticated user's own corrections with current status."""
    stmt = (
        select(Correction)
        .where(Correction.user_id == uuid.UUID(current_user["id"]))
        .order_by(desc(Correction.created_at))
        .limit(100)
    )
    result = await db.execute(stmt)
    corrections = result.scalars().all()
    return [_serialize_correction(c) for c in corrections]


@router.get("/admin")
async def list_corrections(
    status: Optional[str] = Query(None),
    workspace_id: Optional[str] = Query(None),
    issue_type: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all corrections with filters. Admin only."""
    _require_admin(current_user)

    filters = []
    if status:
        filters.append(Correction.status == status)
    if workspace_id:
        filters.append(Correction.workspace_id == workspace_id)
    if issue_type:
        filters.append(Correction.issue_type == issue_type)
    if from_date:
        filters.append(Correction.created_at >= from_date)
    if to_date:
        filters.append(Correction.created_at <= to_date)

    stmt = (
        select(Correction)
        .where(and_(*filters) if filters else True)
        .order_by(desc(Correction.created_at))
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    result = await db.execute(stmt)
    corrections = result.scalars().all()
    return [_serialize_correction(c) for c in corrections]


@router.put("/admin/{correction_id}")
async def update_correction(
    correction_id: str,
    body: UpdateCorrectionRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Approve, reject, or escalate a correction. Admin only."""
    _require_admin(current_user)
    cid = uuid.UUID(correction_id)
    rid = uuid.UUID(current_user["id"])

    try:
        if body.action == "approve":
            correction, eval_query = await approve_correction(cid, rid, db)
            return {
                **_serialize_correction(correction),
                "eval_query_id": str(eval_query.id) if eval_query else None,
            }
        elif body.action == "reject":
            correction = await reject_correction(cid, rid, body.note, db)
            return _serialize_correction(correction)
        else:
            correction = await escalate_correction(cid, rid, db)
            return _serialize_correction(correction)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/admin/{correction_id}/note", status_code=201)
async def add_note(
    correction_id: str,
    body: AddNoteRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Add an internal reviewer note to a correction. Admin only."""
    _require_admin(current_user)
    note = await add_correction_note(
        correction_id=uuid.UUID(correction_id),
        author_id=uuid.UUID(current_user["id"]),
        note_text=body.note_text,
        db=db,
    )
    return {
        "id": str(note.id),
        "correction_id": str(note.correction_id),
        "author_id": str(note.author_id),
        "note_text": note.note_text,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }


@router.get("/admin/trends")
async def correction_trends(
    workspace_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Weekly correction counts by issue type for last 8 weeks. Admin only."""
    _require_admin(current_user)
    return await get_correction_trends(workspace_id=workspace_id, db=db)


@router.get("/admin/export")
async def export_corrections(
    workspace_id: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Export corrections as CSV. Admin only."""
    _require_admin(current_user)

    filters = []
    if workspace_id:
        filters.append(Correction.workspace_id == workspace_id)
    if from_date:
        filters.append(Correction.created_at >= from_date)
    if to_date:
        filters.append(Correction.created_at <= to_date)

    stmt = (
        select(Correction)
        .where(and_(*filters) if filters else True)
        .order_by(desc(Correction.created_at))
    )
    result = await db.execute(stmt)
    corrections = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "created_at", "workspace_id", "issue_type", "status",
        "reporter_confidence", "incorrect_excerpt", "suggested_correction",
        "reviewer_id", "reviewed_at", "eval_query_created",
    ])
    for c in corrections:
        writer.writerow([
            str(c.id), c.created_at, c.workspace_id, c.issue_type, c.status,
            c.reporter_confidence, c.incorrect_excerpt or "", c.suggested_correction or "",
            str(c.reviewer_id) if c.reviewer_id else "", c.reviewed_at or "",
            c.eval_query_created,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=corrections_export.csv"},
    )
