from sqlalchemy import Column, String, DateTime, func, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid

class ResearchProject(Base):
    __tablename__ = "research_projects"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ResearchPaper(Base):
    __tablename__ = "research_papers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), nullable=True)
    title = Column(String, nullable=False)
    authors = Column(JSON, default=[])
    abstract = Column(String, nullable=True)
    published_year = Column(String, nullable=True)
    embedding = Column(Vector(1536), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ResearchFinding(Base):
    __tablename__ = "research_findings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("research_papers.id", ondelete="CASCADE"), nullable=False)
    statement = Column(String, nullable=False)
    evidence_quote = Column(String, nullable=True)
    methodology = Column(String, nullable=True)
    embedding = Column(Vector(1536), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ContradictionReport(Base):
    __tablename__ = "research_contradictions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    finding_a_id = Column(UUID(as_uuid=True), ForeignKey("research_findings.id", ondelete="CASCADE"), nullable=False)
    finding_b_id = Column(UUID(as_uuid=True), ForeignKey("research_findings.id", ondelete="CASCADE"), nullable=False)
    description = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
