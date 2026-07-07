from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from app.models.export_job import ExportStatus, ExportFormat

class ExportJobCreate(BaseModel):
    format: ExportFormat
    export_type: str
    payload: Dict[str, Any]

class ExportJobResponse(BaseModel):
    id: UUID
    status: ExportStatus
    format: ExportFormat
    export_type: str
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
