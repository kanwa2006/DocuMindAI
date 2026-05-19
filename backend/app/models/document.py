import enum
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base

class DocumentStatus(str, enum.Enum):
    PENDING_UPLOAD = "PENDING_UPLOAD"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED = "FAILED"

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    filename = Column(String, index=True, nullable=False)
    file_hash = Column(String, index=True, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_path = Column(String, nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING_UPLOAD, nullable=False)
    
    # Workspace/User ownership mappings
    owner_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=True)
    chat_session_id = Column(UUID(as_uuid=True), index=True, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
