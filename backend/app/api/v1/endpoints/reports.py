import secrets
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, and_

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.report_share import ReportShare, MessageNote
from app.models.chat import ChatSession, ChatMessage

logger = logging.getLogger(__name__)
router = APIRouter()

_EXPIRY_DAYS_ALLOWED = {1, 3, 7, 30}


# ── Schemas ───────────────────────────────────────────────────────────────────

class GenerateReportRequest(BaseModel):
    title: Optional[str] = None
    sections: Optional[dict] = None
    branding: Optional[dict] = None
    watermark: Optional[dict] = None
    footer_options: Optional[dict] = None


class CreateShareRequest(BaseModel):
    expiry_days: int = 7
    watermark_text: Optional[str] = None

    @field_validator("expiry_days")
    @classmethod
    def validate_expiry(cls, v: int) -> int:
        if v not in _EXPIRY_DAYS_ALLOWED:
            raise ValueError(f"expiry_days must be one of {sorted(_EXPIRY_DAYS_ALLOWED)}")
        return v


class CreateNoteRequest(BaseModel):
    note_text: str

    @field_validator("note_text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("note_text cannot be empty")
        return v[:1000]


# ── Report Generation (9-F2, 9-F3) ───────────────────────────────────────────

@router.post("/export/{session_id}/report")
async def generate_report(
    session_id: str,
    body: GenerateReportRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Generate an executive PDF report for a session.
    LLM call for executive summary is hard-capped at 200 output tokens.
    Max response time: 30s.
    """
    from app.tasks.report_tasks import generate_session_report

    uid = uuid.UUID(current_user["id"])
    sid = uuid.UUID(session_id)

    session = await db.get(ChatSession, sid)
    if session is None or session.owner_id != uid:
        raise HTTPException(status_code=404, detail="Session not found")

    config = body.model_dump(exclude_none=True)
    if not config.get("title"):
        config["title"] = (
            f"{session.workspace_type.title()} Analysis — "
            f"{datetime.utcnow().strftime('%Y-%m-%d')}"
        )
    config["prepared_by"] = current_user.get("email", "DocuMindAI User")
    config["workspace_type"] = session.workspace_type

    try:
        pdf_bytes = await generate_session_report(sid, config, db)
    except Exception as exc:
        logger.error("Report generation failed session=%s: %s", sid, exc)
        raise HTTPException(status_code=500, detail="Report generation failed")

    safe_title = (config.get("title", "report") or "report").replace(" ", "_").replace("/", "-")
    filename = f"{safe_title[:60]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Review Link / Share (9-F3) ────────────────────────────────────────────────

@router.post("/sessions/{session_id}/share", status_code=201)
async def create_share_link(
    session_id: str,
    body: CreateShareRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Create a time-limited read-only review link for a session.
    Rate limited to 5/hour per user (enforced externally by rate limiter middleware).
    """
    uid = uuid.UUID(current_user["id"])
    sid = uuid.UUID(session_id)

    session = await db.get(ChatSession, sid)
    if session is None or session.owner_id != uid:
        raise HTTPException(status_code=404, detail="Session not found")

    token = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(days=body.expiry_days)

    share = ReportShare(
        session_id=sid,
        user_id=uid,
        share_token=token,
        expires_at=expires_at,
        watermark_text=body.watermark_text,
        report_config={},
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)

    return {
        "share_token": token,
        "share_url": f"/r/{token}",
        "expires_at": expires_at.isoformat(),
        "view_count": 0,
    }


@router.get("/r/{share_token}")
async def view_shared_report(
    share_token: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Public read-only endpoint — no auth required.
    Validates token existence and expiry, increments view_count,
    returns report data for the frontend /r/[token] page.
    Returns 410 Gone for missing or expired tokens.
    """
    result = await db.execute(
        select(ReportShare).where(ReportShare.share_token == share_token)
    )
    share = result.scalar_one_or_none()

    if share is None:
        raise HTTPException(
            status_code=410,
            detail="This report link has expired or does not exist.",
        )

    now = datetime.now(timezone.utc)
    expires = share.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        raise HTTPException(
            status_code=410,
            detail="This report link has expired.",
        )

    share.view_count = (share.view_count or 0) + 1
    await db.commit()

    session = await db.get(ChatSession, share.session_id)
    workspace_type = session.workspace_type if session else "general"

    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == share.session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = msg_result.scalars().all()

    report_config = share.report_config or {}
    return {
        "title": report_config.get("title", "Shared Report"),
        "workspace_type": workspace_type,
        "watermark_text": share.watermark_text,
        "expires_at": share.expires_at.isoformat(),
        "view_count": share.view_count,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
            if m.role in ("user", "assistant")
        ],
    }


# ── Admin Report Access Log (9-F3) ────────────────────────────────────────────

@router.get("/admin/reports/access-log")
async def report_access_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Admin-only view of all report shares with view counts."""
    roles = current_user.get("roles", [])
    if "admin" not in roles and "super_admin" not in roles:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(
        select(ReportShare)
        .order_by(desc(ReportShare.created_at))
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    shares = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "session_id": str(s.session_id),
            "user_id": str(s.user_id),
            "share_token_prefix": s.share_token[:8] + "…",
            "expires_at": s.expires_at.isoformat(),
            "view_count": s.view_count,
            "watermark_text": s.watermark_text,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in shares
    ]


# ── Message Notes (9-F4) ─────────────────────────────────────────────────────

@router.post("/messages/{message_id}/notes", status_code=201)
async def create_message_note(
    message_id: str,
    body: CreateNoteRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Add a private note to a message. Only visible to the note's author."""
    uid = uuid.UUID(current_user["id"])
    mid = uuid.UUID(message_id)
    note = MessageNote(message_id=mid, user_id=uid, note_text=body.note_text)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return _serialize_note(note)


@router.get("/messages/{message_id}/notes")
async def list_message_notes(
    message_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List caller's notes on a specific message."""
    uid = uuid.UUID(current_user["id"])
    mid = uuid.UUID(message_id)
    result = await db.execute(
        select(MessageNote)
        .where(and_(MessageNote.message_id == mid, MessageNote.user_id == uid))
        .order_by(MessageNote.created_at)
    )
    return [_serialize_note(n) for n in result.scalars().all()]


@router.delete("/messages/{message_id}/notes/{note_id}", status_code=204)
async def delete_message_note(
    message_id: str,
    note_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a private message note. Only the author can delete."""
    uid = uuid.UUID(current_user["id"])
    note = await db.get(MessageNote, uuid.UUID(note_id))
    if (
        note is None
        or note.user_id != uid
        or note.message_id != uuid.UUID(message_id)
    ):
        raise HTTPException(status_code=404, detail="Note not found")
    await db.delete(note)
    await db.commit()


# ── Document Smart Naming (9-G1) ──────────────────────────────────────────────

@router.post("/documents/{document_id}/suggest-name")
async def suggest_document_name(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Suggest a clean filename for a generically-named document.
    Calls LLM with the first 500 chars of extracted text.
    Returns {suggested_name: str | null}.
    """
    from app.models.document import Document
    from app.services.llm_service import get_llm_service

    uid = uuid.UUID(current_user["id"])
    doc = await db.get(Document, uuid.UUID(document_id))
    if doc is None or getattr(doc, "owner_id", None) != uid:
        raise HTTPException(status_code=404, detail="Document not found")

    extracted_text: str = getattr(doc, "extracted_text", "") or ""
    sample = extracted_text[:500]
    if not sample:
        return {"suggested_name": None}

    try:
        llm = get_llm_service()
        prompt = (
            "What is this document? Respond with ONLY a short filename "
            "(max 50 chars, no extension, use underscores). "
            "Examples: HDFC_Annual_Report_FY2024, NDA_Agreement_ABC_Corp, "
            "Employment_Contract_Senior_Engineer\n\n"
            f"{sample}"
        )
        suggested = await llm.generate(system_prompt="You are a document naming assistant.", user_prompt=prompt)
        suggested = suggested.strip().replace(" ", "_")[:50]
    except Exception as exc:
        logger.warning("Name suggestion LLM call failed: %s", exc)
        return {"suggested_name": None}

    return {"suggested_name": suggested}


@router.put("/documents/{document_id}/display-name")
async def set_display_name(
    document_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Set a user-visible display_name on a document (distinct from storage filename)."""
    from app.models.document import Document

    uid = uuid.UUID(current_user["id"])
    doc = await db.get(Document, uuid.UUID(document_id))
    if doc is None or getattr(doc, "owner_id", None) != uid:
        raise HTTPException(status_code=404, detail="Document not found")

    display_name = str(body.get("display_name", "")).strip()[:50]
    doc.display_name = display_name  # type: ignore[attr-defined]
    await db.commit()
    return {"display_name": display_name}


# ── Serializers ───────────────────────────────────────────────────────────────

def _serialize_note(n: MessageNote) -> dict:
    return {
        "id": str(n.id),
        "message_id": str(n.message_id),
        "user_id": str(n.user_id),
        "note_text": n.note_text,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }
