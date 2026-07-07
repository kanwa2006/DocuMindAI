from sqlalchemy import Column, String, DateTime, func, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base
import uuid

class Contract(Base):
    __tablename__ = "legal_contracts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), nullable=False) # Reference to underlying raw PDF/DOCX Document
    title = Column(String, nullable=False)
    party_name = Column(String, nullable=True)
    contract_type = Column(String, nullable=True) # NDA, MSA, DPA, EMPLOYMENT
    status = Column(String, default="DRAFT") # DRAFT, IN_REVIEW, APPROVED, REJECTED, EXECUTED
    risk_score = Column(String, nullable=True) # HIGH, MEDIUM, LOW
    metadata_json = Column(JSON, default={}) # Effective dates, jurisdictions, values
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ComplianceRule(Base):
    __tablename__ = "legal_compliance_rules"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False) # LIABILITY, DATA_PRIVACY, TERMINATION, INDEMNIFICATION
    rule_description = Column(String, nullable=False)
    mandatory = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Clause(Base):
    __tablename__ = "legal_clauses"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("legal_contracts.id", ondelete="CASCADE"), nullable=False)
    section_name = Column(String, nullable=True)
    original_text = Column(String, nullable=False)
    clause_type = Column(String, nullable=True) # E.g., Confidentiality
    risk_level = Column(String, nullable=True) # HIGH, MEDIUM, LOW, COMPLIANT
    compliance_notes = Column(String, nullable=True)
    embedding = Column(Vector(1536), nullable=True) # For semantic search and clause similarity
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RedlineSuggestion(Base):
    __tablename__ = "legal_redlines"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    clause_id = Column(UUID(as_uuid=True), ForeignKey("legal_clauses.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("legal_compliance_rules.id", ondelete="SET NULL"), nullable=True)
    suggested_text = Column(String, nullable=False)
    explanation = Column(String, nullable=False)
    status = Column(String, default="PENDING") # PENDING, ACCEPTED, REJECTED
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ApprovalWorkflow(Base):
    __tablename__ = "legal_approvals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("legal_contracts.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(UUID(as_uuid=True), nullable=False)
    stage = Column(String, default="LEGAL_REVIEW")
    status = Column(String, default="PENDING") # PENDING, APPROVED, CHANGES_REQUESTED
    comments = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
