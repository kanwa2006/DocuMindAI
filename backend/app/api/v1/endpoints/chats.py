import uuid
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import or_

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.chat import ChatSession, ChatMessage
from app.models.document import Document
from pydantic import BaseModel, UUID4

router = APIRouter()

class ChatSessionCreate(BaseModel):
    title: str = "New Chat"
    workspace_type: str = "general"

class ChatSessionResponse(BaseModel):
    id: UUID4
    title: str
    workspace_type: str
    is_pinned: bool
    is_archived: bool
    class Config:
        orm_mode = True

class ChatMessageCreate(BaseModel):
    role: str
    content: str

class ChatMessageResponse(BaseModel):
    id: UUID4
    role: str
    content: str
    class Config:
        orm_mode = True

@router.post("", response_model=ChatSessionResponse)
async def create_chat_session(
    request: ChatSessionCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    session = ChatSession(
        owner_id=uuid.UUID(current_user["id"]),
        workspace_id=uuid.UUID(current_user["workspace_id"]),
        title=request.title,
        workspace_type=request.workspace_type
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

@router.get("", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    workspace_type: str = "general",
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ChatSession).where(
        ChatSession.workspace_id == uuid.UUID(current_user["workspace_id"]),
        ChatSession.workspace_type == workspace_type,
        ChatSession.is_archived == False
    )
    
    if search:
        # Search title or message content
        stmt = stmt.outerjoin(ChatMessage).where(
            or_(
                ChatSession.title.ilike(f"%{search}%"),
                ChatMessage.content.ilike(f"%{search}%")
            )
        ).distinct()

    stmt = stmt.order_by(ChatSession.updated_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(stmt)
    return result.scalars().all()

@router.patch("/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: str,
    update_data: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ChatSession).where(
        ChatSession.id == uuid.UUID(session_id),
        ChatSession.workspace_id == uuid.UUID(current_user["workspace_id"])
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    for key, value in update_data.items():
        if hasattr(session, key):
            setattr(session, key, value)
            
    await db.commit()
    await db.refresh(session)
    return session

@router.delete("/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ChatSession).where(
        ChatSession.id == uuid.UUID(session_id),
        ChatSession.workspace_id == uuid.UUID(current_user["workspace_id"])
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    await db.delete(session)
    await db.commit()
    return {"status": "deleted"}

@router.get("/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify ownership
    stmt = select(ChatSession).where(
        ChatSession.id == uuid.UUID(session_id),
        ChatSession.workspace_id == uuid.UUID(current_user["workspace_id"])
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    msg_stmt = select(ChatMessage).where(
        ChatMessage.session_id == uuid.UUID(session_id)
    ).order_by(ChatMessage.created_at.asc()).limit(limit).offset(offset)
    msg_result = await db.execute(msg_stmt)
    
    return msg_result.scalars().all()

@router.post("/{session_id}/messages", response_model=ChatMessageResponse)
async def create_chat_message(
    session_id: str,
    request: ChatMessageCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify ownership
    stmt = select(ChatSession).where(
        ChatSession.id == uuid.UUID(session_id),
        ChatSession.workspace_id == uuid.UUID(current_user["workspace_id"])
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    message = ChatMessage(
        session_id=uuid.UUID(session_id),
        role=request.role,
        content=request.content
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message
