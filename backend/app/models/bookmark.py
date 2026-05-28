import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSON
from app.db.base_class import Base


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(String, nullable=False)
    message_content = Column(Text, nullable=False)
    citations = Column(JSON, nullable=True)
    tags = Column(ARRAY(String), default=[], nullable=False, server_default="{}")
    workspace = Column(String, nullable=False, default="general")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
