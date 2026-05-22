import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.bookmark import Bookmark

router = APIRouter()


class BookmarkCreate(BaseModel):
    session_id: UUID4
    message_id: str
    content: str
    citations: Optional[list] = None
    tags: Optional[List[str]] = []
    workspace: Optional[str] = "general"


class BookmarkTagUpdate(BaseModel):
    tags: List[str]


class BookmarkResponse(BaseModel):
    id: UUID4
    session_id: UUID4
    message_id: str
    message_content: str
    citations: Optional[list] = None
    tags: List[str]
    workspace: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=BookmarkResponse)
async def create_bookmark(
    body: BookmarkCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(str(current_user["id"]))
    bookmark = Bookmark(
        id=uuid.uuid4(),
        user_id=user_id,
        session_id=body.session_id,
        message_id=body.message_id,
        message_content=body.content,
        citations=body.citations,
        tags=body.tags or [],
        workspace=body.workspace or "general",
    )
    db.add(bookmark)
    await db.commit()
    await db.refresh(bookmark)
    return bookmark


@router.get("", response_model=List[BookmarkResponse])
async def list_bookmarks(
    tag: Optional[str] = None,
    workspace: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(str(current_user["id"]))
    stmt = select(Bookmark).where(Bookmark.user_id == user_id).order_by(desc(Bookmark.created_at))
    if workspace:
        stmt = stmt.where(Bookmark.workspace == workspace)
    result = await db.execute(stmt)
    bookmarks = result.scalars().all()
    if tag:
        bookmarks = [b for b in bookmarks if tag in (b.tags or [])]
    return bookmarks


@router.delete("/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(str(current_user["id"]))
    result = await db.execute(
        select(Bookmark).where(Bookmark.id == bookmark_id, Bookmark.user_id == user_id)
    )
    bookmark = result.scalar_one_or_none()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    await db.delete(bookmark)
    await db.commit()
    return {"success": True}


@router.patch("/{bookmark_id}/tags")
async def update_tags(
    bookmark_id: uuid.UUID,
    body: BookmarkTagUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(str(current_user["id"]))
    result = await db.execute(
        select(Bookmark).where(Bookmark.id == bookmark_id, Bookmark.user_id == user_id)
    )
    bookmark = result.scalar_one_or_none()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    bookmark.tags = body.tags
    await db.commit()
    return {"success": True, "tags": body.tags}
