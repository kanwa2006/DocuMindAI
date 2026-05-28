from sqlalchemy import Column, String, DateTime, func, JSON, ForeignKey, Float, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid

class JobRole(Base):
    __tablename__ = "hr_job_roles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    title = Column(String, nullable=False)
    department = Column(String, nullable=True)
    description = Column(String, nullable=True)
    requirements = Column(JSON, nullable=True) # {"skills": [], "experience": ""}
    status = Column(String, default="OPEN") # OPEN, CLOSED, DRAFT
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class CandidateProfile(Base):
    __tablename__ = "hr_candidates"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), nullable=False) # Reference to the uploaded resume Document
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    skills = Column(JSON, default=[])
    experience_years = Column(Float, nullable=True)
    education = Column(JSON, default=[])
    extracted_data = Column(JSON, nullable=True) # Full parsed JSON from LLM
    embedding = Column(Vector(1536), nullable=True) # PHASE 2: Semantic Candidate Search
    stage = Column(String, default="applied")  # 6-H1: pipeline stage tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class CandidateNote(Base):
    """PHASE 1: Recruiter Collaboration"""
    __tablename__ = "hr_candidate_notes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("hr_candidates.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(UUID(as_uuid=True), nullable=False) # The recruiter
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
class Interview(Base):
    """PHASE 4: Interview System"""
    __tablename__ = "hr_interviews"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    match_id = Column(UUID(as_uuid=True), ForeignKey("hr_job_matches.id", ondelete="CASCADE"), nullable=False)
    interviewer_id = Column(UUID(as_uuid=True), nullable=False)
    scheduled_time = Column(DateTime(timezone=True), nullable=True)
    scorecard = Column(JSON, nullable=True) # Ratings and notes
    status = Column(String, default="SCHEDULED") # SCHEDULED, COMPLETED, CANCELED
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class JobMatch(Base):
    __tablename__ = "hr_job_matches"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("hr_job_roles.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("hr_candidates.id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    fit_score = Column(Float, nullable=True) # 0.0 to 100.0 — LLM-assigned ATS score
    semantic_score = Column(Float, nullable=True) # 6-H2: cosine similarity score (0.0–1.0)
    final_score = Column(Float, nullable=True) # 6-H2: 0.6*llm + 0.4*semantic*100 blended
    match_analysis = Column(JSON, nullable=True) # {"pros": [], "cons": [], "missing_skills": []}
    status = Column(String, default="NEW") # NEW, SHORTLISTED, REJECTED, INTERVIEW
    recruiter_notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
