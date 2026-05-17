from sqlalchemy import Column, String, DateTime, func, JSON, ForeignKey, Float, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid

class StudyNote(Base):
    __tablename__ = "study_notes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), nullable=True) # Linked document
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    tags = Column(JSON, default=[])
    embedding = Column(Vector(1536), nullable=True) # PHASE 2: Study Vector Search
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FlashcardDeck(Base):
    __tablename__ = "study_flashcard_decks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Flashcard(Base):
    __tablename__ = "study_flashcards"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    deck_id = Column(UUID(as_uuid=True), ForeignKey("study_flashcard_decks.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), nullable=True) # For grounded citations
    front = Column(String, nullable=False) # Question / Concept
    back = Column(String, nullable=False) # Answer / Explanation
    citation = Column(String, nullable=True)
    embedding = Column(Vector(1536), nullable=True) # PHASE 2: Study Vector Search
    
    # Spaced Repetition (SuperMemo-2 style)
    repetition_count = Column(Integer, default=0)
    easiness_factor = Column(Float, default=2.5)
    interval_days = Column(Integer, default=0)
    next_review_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class QuizAttempt(Base):
    __tablename__ = "study_quiz_attempts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    responses = Column(JSON, default={}) # Store exact responses and right/wrong status
    created_at = Column(DateTime(timezone=True), server_default=func.now())
