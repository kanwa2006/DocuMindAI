import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, UUID4, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update as sa_update, desc

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.notification import Notification

router = APIRouter()


class NotificationResponse(BaseModel):
    id: UUID4
    type: str
    title: str
    body: Optional[str] = None
    action_url: Optional[str] = Field(None, validation_alias="link")
    is_read: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return unread + last 20 read notifications for the current user."""
    user_id = uuid.UUID(str(current_user["id"]))
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(desc(Notification.created_at))
        .limit(40)
    )
    rows = result.scalars().all()
    # Keep all unread + up to 20 most-recent read
    unread = [n for n in rows if not n.is_read]
    read = [n for n in rows if n.is_read][:20]
    return unread + read


@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(str(current_user["id"]))
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    await db.commit()
    return {"success": True}


@router.patch("/read-all")
async def mark_all_read(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(str(current_user["id"]))
    await db.execute(
        sa_update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.commit()
    return {"success": True}
