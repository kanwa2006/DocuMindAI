"""
P0-9 — tenant isolation.

`workspace_id` on these tables is derived from a workspace SLUG
(`uuid5(NAMESPACE_DNS, "legal"|"finance"|...)`), so it is IDENTICAL for every
user in the system: it partitions rows by CATEGORY, not by tenant. Queries
filtering on `workspace_id` alone therefore returned every user's rows.

The tenant key is `owner_id`, declared once by the `TenantScoped` mixin. The
mixin also opts these tables into automatic query scoping — see
`app/core/tenant_scope.py`. Reads are filtered by the session hook; writes must
still set `owner_id` explicitly (it is NOT NULL, so a miss fails loudly).
"""
from sqlalchemy import Column, String, DateTime, func, JSON, ForeignKey, Float, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.core.tenant_scope import TenantScoped
import uuid

class StudyNote(TenantScoped, Base):
    __tablename__ = "study_notes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), nullable=True) # Linked document
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    tags = Column(JSON, default=[])
    embedding = Column(Vector(1024), nullable=True) # C-7: matches embedding_service (bge-m3, 1024-dim); was 1536
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FlashcardDeck(TenantScoped, Base):
    __tablename__ = "study_flashcard_decks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Flashcard(TenantScoped, Base):
    __tablename__ = "study_flashcards"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    deck_id = Column(UUID(as_uuid=True), ForeignKey("study_flashcard_decks.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), nullable=True) # For grounded citations
    front = Column(String, nullable=False) # Question / Concept
    back = Column(String, nullable=False) # Answer / Explanation
    citation = Column(String, nullable=True)
    embedding = Column(Vector(1024), nullable=True) # C-7: matches embedding_service (bge-m3, 1024-dim); was 1536

    # Spaced Repetition (SuperMemo-2 style)
    repetition_count = Column(Integer, default=0)
    easiness_factor = Column(Float, default=2.5)
    interval_days = Column(Integer, default=0)
    next_review_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class StudyQuiz(TenantScoped, Base):
    """Stores generated quizzes with correct answers server-side (anti-cheat)."""
    __tablename__ = "study_quizzes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    topic = Column(String, nullable=False)
    difficulty = Column(String, default="medium")
    doc_ids = Column(JSON, default=[])
    questions = Column(JSON, nullable=False)  # Full questions WITH correct_index
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class QuizAttempt(TenantScoped, Base):
    __tablename__ = "study_quiz_attempts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    responses = Column(JSON, default={}) # Store exact responses and right/wrong status
    created_at = Column(DateTime(timezone=True), server_default=func.now())
