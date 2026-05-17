from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
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

class DocumentResponse(DocumentBase):
    id: UUID
    status: DocumentStatus
    owner_id: UUID
    workspace_id: UUID | None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
