import uuid
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base


class SavedQueryTemplate(Base):
    __tablename__ = "saved_query_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(40), nullable=False)
    query_text = Column(String, nullable=False)
    workspace_id = Column(String, nullable=False)
    notes = Column(String, nullable=True)
    use_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Notification lives in notification.py — re-export for backward compat
from app.models.notification import Notification as Notification  # noqa: F401
