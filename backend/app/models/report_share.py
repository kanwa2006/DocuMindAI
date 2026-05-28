import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.base import Base


class ReportShare(Base):
    __tablename__ = "report_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    share_token = Column(String, unique=True, nullable=False, index=True)  # secrets.token_urlsafe(24)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    view_count = Column(Integer, nullable=False, default=0)
    watermark_text = Column(String, nullable=True)
    report_config = Column(JSONB, nullable=True)  # {title, sections, branding, footer}
    report_pdf_key = Column(String, nullable=True)  # S3/local path of cached PDF
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MessageNote(Base):
    __tablename__ = "message_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    note_text = Column(String(1000), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
