import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, and_

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.saved_query_template import SavedQueryTemplate, Notification
from app.models.document import Document

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateTemplateRequest(BaseModel):
    name: str
    query_text: str
    workspace_id: str
    notes: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty")
        if len(v) > 40:
            raise ValueError("name must be ≤40 chars")
        return v

    @field_validator("query_text")
    @classmethod
    def validate_query_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query_text cannot be empty")
        return v


class ScheduleReportRequest(BaseModel):
    workspace_id: str
    is_active: bool = True


# ── Query Templates ───────────────────────────────────────────────────────────

@router.get("/query-templates")
async def list_templates(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List user's saved query templates ordered by use count descending."""
    uid = uuid.UUID(current_user["id"])
    result = await db.execute(
        select(SavedQueryTemplate)
        .where(SavedQueryTemplate.user_id == uid)
        .order_by(desc(SavedQueryTemplate.use_count), desc(SavedQueryTemplate.created_at))
    )
    return [_serialize_template(t) for t in result.scalars().all()]


@router.post("/query-templates", status_code=201)
async def create_template(
    body: CreateTemplateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a saved query template."""
    uid = uuid.UUID(current_user["id"])
    template = SavedQueryTemplate(
        user_id=uid,
        name=body.name,
        query_text=body.query_text,
        workspace_id=body.workspace_id,
        notes=body.notes,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return _serialize_template(template)


@router.delete("/query-templates/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a saved query template. Only the owner can delete."""
    uid = uuid.UUID(current_user["id"])
    t = await db.get(SavedQueryTemplate, uuid.UUID(template_id))
    if t is None or t.user_id != uid:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(t)
    await db.commit()


@router.post("/query-templates/{template_id}/use")
async def use_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Increment use_count and return the template text for paste-into-input."""
    uid = uuid.UUID(current_user["id"])
    t = await db.get(SavedQueryTemplate, uuid.UUID(template_id))
    if t is None or t.user_id != uid:
        raise HTTPException(status_code=404, detail="Template not found")
    t.use_count = (t.use_count or 0) + 1
    await db.commit()
    return {"query_text": t.query_text, "use_count": t.use_count}


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications")
async def list_notifications(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List unread notifications for the current user (most recent 20)."""
    uid = uuid.UUID(current_user["id"])
    result = await db.execute(
        select(Notification)
        .where(and_(Notification.user_id == uid, Notification.is_read == False))
        .order_by(desc(Notification.created_at))
        .limit(20)
    )
    return [_serialize_notification(n) for n in result.scalars().all()]


@router.post("/notifications/{notification_id}/read", status_code=204)
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Mark a single notification as read."""
    uid = uuid.UUID(current_user["id"])
    n = await db.get(Notification, uuid.UUID(notification_id))
    if n is None or n.user_id != uid:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    await db.commit()


@router.post("/notifications/read-all", status_code=204)
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Mark all unread notifications as read."""
    uid = uuid.UUID(current_user["id"])
    result = await db.execute(
        select(Notification)
        .where(and_(Notification.user_id == uid, Notification.is_read == False))
    )
    for n in result.scalars().all():
        n.is_read = True
    await db.commit()


# ── Document Change Detection (9-E) ──────────────────────────────────────────

@router.get("/documents/{document_id}/change-detection")
async def document_change_detection(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Check if a newer version of the same filename exists for this user.
    Returns newer_version_exists=True when the same filename has been uploaded
    more than once. Used to show the DocumentChangeAlert in the UI.
    """
    uid = uuid.UUID(current_user["id"])
    try:
        doc_id = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid document ID")

    doc = await db.get(Document, doc_id)
    if doc is None or getattr(doc, "owner_id", None) != uid:
        raise HTTPException(status_code=404, detail="Document not found")

    filename = getattr(doc, "filename", None)
    if not filename:
        return {"newer_version_exists": False, "previous_session_id": None}

    result = await db.execute(
        select(Document)
        .where(
            and_(
                Document.owner_id == uid,
                Document.filename == filename,
                Document.id != doc_id,
            )
        )
        .order_by(desc(Document.created_at))
        .limit(1)
    )
    other = result.scalar_one_or_none()
    if other is None:
        return {"newer_version_exists": False, "previous_session_id": None}

    return {
        "newer_version_exists": True,
        "previous_session_id": None,  # session linkage deferred — doc<→session join not needed for alert
        "previous_doc_id": str(other.id),
        "previous_created_at": other.created_at.isoformat() if other.created_at else None,
    }


# ── Scheduled Reports (9-G5) ──────────────────────────────────────────────────

@router.post("/sessions/{session_id}/schedule", status_code=201)
async def schedule_report(
    session_id: str,
    body: ScheduleReportRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create or update a weekly scheduled report for a session."""
    from app.models.workspace_template import ScheduledReport
    from app.tasks.report_tasks import _next_monday_8am

    uid = uuid.UUID(current_user["id"])
    sid = uuid.UUID(session_id)

    result = await db.execute(
        select(ScheduledReport).where(
            and_(ScheduledReport.user_id == uid, ScheduledReport.session_id == sid)
        )
    )
    existing = result.scalar_one_or_none()
    next_run = _next_monday_8am(datetime.now(timezone.utc))

    if existing:
        existing.is_active = body.is_active
        if body.is_active:
            existing.next_run_at = next_run
        await db.commit()
        await db.refresh(existing)
        return _serialize_scheduled(existing)

    sched = ScheduledReport(
        user_id=uid,
        session_id=sid,
        workspace_id=body.workspace_id,
        next_run_at=next_run,
        is_active=True,
    )
    db.add(sched)
    await db.commit()
    await db.refresh(sched)
    return _serialize_scheduled(sched)


@router.get("/sessions/{session_id}/schedule")
async def get_schedule(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get scheduled report status for a session."""
    from app.models.workspace_template import ScheduledReport

    uid = uuid.UUID(current_user["id"])
    sid = uuid.UUID(session_id)
    result = await db.execute(
        select(ScheduledReport).where(
            and_(ScheduledReport.user_id == uid, ScheduledReport.session_id == sid)
        )
    )
    sched = result.scalar_one_or_none()
    if sched is None:
        return {"is_active": False, "next_run_at": None, "last_run_at": None}
    return _serialize_scheduled(sched)


# ── Serializers ───────────────────────────────────────────────────────────────

def _serialize_template(t: SavedQueryTemplate) -> dict:
    return {
        "id": str(t.id),
        "user_id": str(t.user_id),
        "name": t.name,
        "query_text": t.query_text,
        "workspace_id": t.workspace_id,
        "notes": t.notes,
        "use_count": t.use_count,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _serialize_notification(n: Notification) -> dict:
    return {
        "id": str(n.id),
        "user_id": str(n.user_id),
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "link": n.link,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


def _serialize_scheduled(s: Any) -> dict:
    return {
        "id": str(s.id),
        "session_id": str(s.session_id),
        "workspace_id": s.workspace_id,
        "frequency": s.frequency,
        "is_active": s.is_active,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
        "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
    }
