from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from typing import Optional
from datetime import datetime
from app.models.document import DocumentStatus

class DocumentBase(BaseModel):
    filename: str
    mime_type: str
    size_bytes: int

class DocumentCreate(DocumentBase):
    file_hash: str
    storage_path: str
    owner_id: UUID
    workspace_id: UUID | None = None
    chat_session_id: UUID | None = None  # P1: per-chat isolation

class DocumentResponse(DocumentBase):
    id: UUID
    status: DocumentStatus
    owner_id: UUID
    workspace_id: UUID | None
    # P1: surface chat_session_id so the frontend can scope its doc rail to
    # the active chat instead of leaking docs across sessions in the same
    # workspace.
    chat_session_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
