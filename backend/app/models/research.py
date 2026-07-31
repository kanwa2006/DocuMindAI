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
from sqlalchemy import Column, String, DateTime, func, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.core.tenant_scope import TenantScoped
import uuid

class ResearchProject(TenantScoped, Base):
    __tablename__ = "research_projects"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ResearchPaper(TenantScoped, Base):
    __tablename__ = "research_papers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), nullable=True)
    title = Column(String, nullable=False)
    authors = Column(JSON, default=[])
    abstract = Column(String, nullable=True)
    published_year = Column(String, nullable=True)
    embedding = Column(Vector(1024), nullable=True)  # C-7: matches embedding_service (bge-m3, 1024-dim); was 1536
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ResearchFinding(TenantScoped, Base):
    __tablename__ = "research_findings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("research_papers.id", ondelete="CASCADE"), nullable=False)
    statement = Column(String, nullable=False)
    evidence_quote = Column(String, nullable=True)
    methodology = Column(String, nullable=True)
    embedding = Column(Vector(1024), nullable=True)  # C-7: matches embedding_service (bge-m3, 1024-dim); was 1536
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ContradictionReport(TenantScoped, Base):
    __tablename__ = "research_contradictions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    finding_a_id = Column(UUID(as_uuid=True), ForeignKey("research_findings.id", ondelete="CASCADE"), nullable=False)
    finding_b_id = Column(UUID(as_uuid=True), ForeignKey("research_findings.id", ondelete="CASCADE"), nullable=False)
    description = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
