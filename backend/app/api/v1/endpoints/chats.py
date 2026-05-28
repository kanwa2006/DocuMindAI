import uuid
import secrets
from datetime import datetime
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import or_, desc, case

from app.db.session import get_db
from app.core.auth import get_current_user
from app.core.workspace import resolve_workspace_id
from app.models.chat import ChatSession, ChatMessage
from app.models.document import Document
from uuid import UUID
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
    created_at: Optional[datetime] = None
    workspace_id: Optional[UUID] = None
    tags: Optional[List[str]] = []
    class Config:
        from_attributes = True

class RenameRequest(BaseModel):
    title: str

class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None
    workspace_type: Optional[str] = None

class ChatTagsUpdate(BaseModel):
    tags: List[str]

class ChatMessageCreate(BaseModel):
    role: str
    content: str

class ChatMessageResponse(BaseModel):
    id: UUID4
    role: str
    content: str
    class Config:
        from_attributes = True

@router.post("", response_model=ChatSessionResponse)
async def create_chat_session(
    request: ChatSessionCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    session = ChatSession(
        owner_id=uuid.UUID(current_user["id"]),
        workspace_id=resolve_workspace_id(current_user["workspace_id"]),
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
        ChatSession.workspace_id == resolve_workspace_id(current_user["workspace_id"]),
        ChatSession.workspace_type == workspace_type,
        ChatSession.is_archived == False
    )
    
    if search:
        stmt = stmt.outerjoin(ChatMessage).where(
            or_(
                ChatSession.title.ilike(f"%{search}%"),
                ChatMessage.content.ilike(f"%{search}%")
            )
        ).distinct()

    # Pinned-first, then created_at DESC
    stmt = stmt.order_by(
        desc(ChatSession.is_pinned),
        desc(ChatSession.created_at)
    ).limit(limit).offset(offset)
    
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/{session_id}/pin", response_model=ChatSessionResponse)
async def toggle_pin_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ChatSession).where(
        ChatSession.id == uuid.UUID(session_id),
        ChatSession.workspace_id == resolve_workspace_id(current_user["workspace_id"])
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.is_pinned = not session.is_pinned
    await db.commit()
    await db.refresh(session)
    return session


@router.patch("/{session_id}/rename", response_model=ChatSessionResponse)
async def rename_session(
    session_id: str,
    request: RenameRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ChatSession).where(
        ChatSession.id == uuid.UUID(session_id),
        ChatSession.workspace_id == resolve_workspace_id(current_user["workspace_id"])
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.title = request.title
    await db.commit()
    await db.refresh(session)
    return session

@router.patch("/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: str,
    update_data: ChatSessionUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ChatSession).where(
        ChatSession.id == uuid.UUID(session_id),
        ChatSession.workspace_id == resolve_workspace_id(current_user["workspace_id"])
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    for key, value in update_data.model_dump(exclude_none=True).items():
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
    # Console-err fix — return clean 400 instead of an uncaught ValueError
    # when the path arg isn't a UUID (was leaking a 500 to the client which
    # the frontend rendered as the generic "Failed to delete chat").
    try:
        session_uuid = uuid.UUID(session_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid chat id.")

    owner_id = uuid.UUID(current_user["id"])
    stmt = select(ChatSession).where(
        ChatSession.id == session_uuid,
        ChatSession.workspace_id == resolve_workspace_id(current_user["workspace_id"]),
        ChatSession.owner_id == owner_id,  # belt-and-suspenders ownership check
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Chat not found.")

    # P1 follow-up — when a chat is deleted, the docs attached to it would
    # otherwise be orphaned (chat_session_id still points at the now-deleted
    # row). Set them to NULL so they don't reappear as ghost entries in a
    # future chat that happens to land on a recycled id. Documents are NOT
    # cascade-deleted because the user may have other uses (clip imports,
    # cross-chat reuse) — orphaning to NULL is the safe middle ground.
    try:
        from sqlalchemy import update as _sa_update
        from app.models.document import Document as _Document
        await db.execute(
            _sa_update(_Document)
            .where(_Document.chat_session_id == session_uuid)
            .where(_Document.owner_id == owner_id)
            .values(chat_session_id=None)
        )
    except Exception as exc:
        # Non-fatal — proceed with chat deletion.
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "[chats/delete] could not orphan docs for %s: %s", session_id, exc
        )

    try:
        await db.delete(session)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        import logging as _logging
        _logging.getLogger(__name__).error(
            "[chats/delete] failed for %s: %s", session_id, exc
        )
        raise HTTPException(
            status_code=500,
            detail="Could not delete chat — please try again or contact support.",
        )
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
        ChatSession.workspace_id == resolve_workspace_id(current_user["workspace_id"])
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
        ChatSession.workspace_id == resolve_workspace_id(current_user["workspace_id"])
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


@router.patch("/{session_id}/tags")
async def update_session_tags(
    session_id: str,
    body: ChatTagsUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Phase 14.5: Update tags on a chat session."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == uuid.UUID(session_id),
            ChatSession.workspace_id == resolve_workspace_id(current_user["workspace_id"]),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.tags = body.tags
    await db.commit()
    return {"success": True, "tags": body.tags}


# ─── Phase 22: Collaboration ──────────────────────────────────────────────────

_PLAN_MAX_COLLABORATORS = {"trial": 1, "professional": 3, "enterprise": 25}
_PLAN_PERMISSIONS = {"trial": ["view_only"], "professional": ["view_only", "view_and_ask"], "enterprise": ["view_only", "view_and_ask"]}


class ShareRequest(BaseModel):
    share_permissions: str = "view_and_ask"


class SharedSessionMessageResponse(BaseModel):
    id: UUID4
    role: str
    content: str
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True


class SharedSessionResponse(BaseModel):
    id: UUID4
    title: str
    workspace_type: str
    share_permissions: str
    owner_id: UUID4
    messages: List[SharedSessionMessageResponse] = []
    class Config:
        from_attributes = True


@router.post("/{session_id}/share")
async def share_session(
    session_id: str,
    body: ShareRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == uuid.UUID(session_id),
            ChatSession.workspace_id == resolve_workspace_id(current_user["workspace_id"]),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_plan = current_user.get("plan", "trial")
    allowed_permissions = _PLAN_PERMISSIONS.get(user_plan, ["view_only"])
    if body.share_permissions not in allowed_permissions:
        raise HTTPException(status_code=403, detail=f"Your plan does not allow '{body.share_permissions}' sharing")

    max_collab = _PLAN_MAX_COLLABORATORS.get(user_plan, 1)
    token = secrets.token_urlsafe(16)
    session.share_token = token
    session.is_shared = True
    session.shared_at = datetime.utcnow()
    session.share_permissions = body.share_permissions
    session.max_collaborators = max_collab
    await db.commit()
    return {
        "share_url": f"https://documindai.com/shared/{token}",
        "share_token": token,
        "share_permissions": body.share_permissions,
        "max_collaborators": max_collab,
    }


@router.delete("/{session_id}/share")
async def unshare_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == uuid.UUID(session_id),
            ChatSession.workspace_id == resolve_workspace_id(current_user["workspace_id"]),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_shared = False
    session.share_token = None
    await db.commit()
    return {"success": True}


# Shared-session public router (no auth required)
shared_router = APIRouter()


@shared_router.get("/shared/{token}", response_model=SharedSessionResponse)
async def get_shared_session(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.share_token == token, ChatSession.is_shared == True)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Shared session not found or sharing has been disabled")
    # Enforce 30-day share-link expiry
    if session.shared_at:
        from datetime import timedelta
        expiry = session.shared_at + timedelta(days=30)
        if datetime.utcnow() > expiry:
            raise HTTPException(status_code=410, detail="This share link has expired")
    return session


class SharedAskRequest(BaseModel):
    question: str


@shared_router.post("/shared/{token}/ask")
async def ask_in_shared_session(token: str, body: SharedAskRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.share_token == token, ChatSession.is_shared == True)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Shared session not found")
    # Enforce 30-day share-link expiry
    if session.shared_at:
        from datetime import timedelta
        expiry = session.shared_at + timedelta(days=30)
        if datetime.utcnow() > expiry:
            raise HTTPException(status_code=410, detail="This share link has expired")
    if session.share_permissions != "view_and_ask":
        raise HTTPException(status_code=403, detail="This session is view-only")

    user_msg = ChatMessage(session_id=session.id, role="user", content=body.question)
    db.add(user_msg)
    await db.flush()

    # Build minimal context from prior messages
    history = "\n".join(
        f"{m.role.upper()}: {m.content}" for m in session.messages[-10:]
    )
    from app.services.llm_service import llm_service
    system_prompt = (
        "You are a helpful AI assistant. A collaborator is asking a question about a shared document session. "
        "Answer based on the conversation history provided."
    )
    user_prompt = f"Conversation history:\n{history}\n\nNew question: {body.question}"
    try:
        answer = await llm_service.provider.generate(system_prompt, user_prompt)
    except Exception:
        answer = "I'm unable to generate a response right now. Please try again."

    assistant_msg = ChatMessage(session_id=session.id, role="assistant", content=answer)
    db.add(assistant_msg)
    await db.commit()
    return {"question": body.question, "answer": answer}
