import uuid
from sqlalchemy import Column, String, DateTime, func, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum

class ExportStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ExportFormat(str, enum.Enum):
    PDF = "PDF"
    DOCX = "DOCX"

class ExportJob(Base):
    __tablename__ = "export_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    
    status = Column(SQLEnum(ExportStatus), default=ExportStatus.PENDING, nullable=False)
    format = Column(SQLEnum(ExportFormat), nullable=False)
    
    export_type = Column(String, nullable=False) # e.g., "GROUNDED_ANSWER"
    payload = Column(JSON, nullable=False)
    
    file_path = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
