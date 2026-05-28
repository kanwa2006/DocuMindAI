import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base_class import Base


class ProactiveInsight(Base):
    __tablename__ = "proactive_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    workspace = Column(String(50), nullable=False)
    insight_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)  # "critical" | "important" | "informational"
    finding = Column(String(500), nullable=False)
    page_reference = Column(Integer, nullable=True)
    was_clicked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
