import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base


class Correction(Base):
    __tablename__ = "corrections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True)
    workspace_id = Column(String, nullable=False, index=True)
    # citation_wrong | answer_incorrect | missing_info | hallucination | source_not_found | other
    issue_type = Column(String, nullable=False)
    incorrect_excerpt = Column(String, nullable=True)
    suggested_correction = Column(String, nullable=True)
    citation_id = Column(String, nullable=True)
    # certain | likely | unsure
    reporter_confidence = Column(String, nullable=False, default="unsure")
    # pending | approved | rejected | escalated
    status = Column(String, nullable=False, default="pending", index=True)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    eval_query_created = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CorrectionNote(Base):
    __tablename__ = "correction_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    correction_id = Column(UUID(as_uuid=True), ForeignKey("corrections.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    note_text = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
