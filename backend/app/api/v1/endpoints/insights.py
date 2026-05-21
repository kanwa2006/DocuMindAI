import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update as sa_update

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.proactive_insight import ProactiveInsight
from app.models.document import Document

router = APIRouter()


class InsightResponse(BaseModel):
    id: UUID4
    document_id: UUID4
    session_id: Optional[UUID4] = None
    workspace: str
    insight_type: str
    severity: str
    finding: str
    page_reference: Optional[int] = None
    was_clicked: bool
    created_at: datetime

    class Config:
        orm_mode = True


class InsightsByDocument(BaseModel):
    document_id: UUID4
    filename: str
    insights: List[InsightResponse]


@router.get("", response_model=List[InsightsByDocument])
async def get_insights_for_session(
    session_id: uuid.UUID = Query(..., description="Chat session ID"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all proactive insights for documents in a session, grouped by document."""
    user_id = uuid.UUID(str(current_user["id"]))

    result = await db.execute(
        select(ProactiveInsight, Document.filename)
        .join(Document, ProactiveInsight.document_id == Document.id)
        .where(
            ProactiveInsight.session_id == session_id,
            Document.owner_id == user_id,
        )
        .order_by(ProactiveInsight.document_id, ProactiveInsight.created_at)
    )
    rows = result.all()

    grouped: dict = {}
    for insight, filename in rows:
        doc_key = str(insight.document_id)
        if doc_key not in grouped:
            grouped[doc_key] = {"document_id": insight.document_id, "filename": filename, "insights": []}
        grouped[doc_key]["insights"].append(insight)

    return [
        InsightsByDocument(
            document_id=v["document_id"],
            filename=v["filename"],
            insights=v["insights"],
        )
        for v in grouped.values()
    ]


@router.patch("/{insight_id}/clicked")
async def mark_insight_clicked(
    insight_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark an insight as clicked (user engaged with it)."""
    user_id = uuid.UUID(str(current_user["id"]))

    result = await db.execute(
        select(ProactiveInsight)
        .join(Document, ProactiveInsight.document_id == Document.id)
        .where(ProactiveInsight.id == insight_id, Document.owner_id == user_id)
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    insight.was_clicked = True
    await db.commit()
    return {"ok": True}
