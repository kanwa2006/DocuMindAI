from sqlalchemy import Column, String, DateTime, func, JSON, ForeignKey, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid

class FinancialDocument(Base):
    __tablename__ = "finance_documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), nullable=False) # Reference to underlying Document
    doc_type = Column(String, nullable=False) # INVOICE, RECEIPT, LEDGER, BANK_STATEMENT
    vendor_name = Column(String, nullable=True)
    total_amount = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    status = Column(String, default="EXTRACTED") # EXTRACTED, RECONCILED, ANOMALY, APPROVED
    extracted_data = Column(JSON, default={}) # Full JSON representation of the doc including tables
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Transaction(Base):
    __tablename__ = "finance_transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    financial_doc_id = Column(UUID(as_uuid=True), ForeignKey("finance_documents.id", ondelete="CASCADE"), nullable=True)
    date = Column(DateTime(timezone=True), nullable=True)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    category = Column(String, nullable=True)
    is_anomaly = Column(Boolean, default=False)
    anomaly_reason = Column(String, nullable=True)
    embedding = Column(Vector(1024), nullable=True) # C-7: matches embedding_service (bge-m3, 1024-dim); was 1536
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditFinding(Base):
    __tablename__ = "finance_audit_findings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    financial_doc_id = Column(UUID(as_uuid=True), ForeignKey("finance_documents.id", ondelete="CASCADE"), nullable=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("finance_transactions.id", ondelete="CASCADE"), nullable=True)
    finding_type = Column(String, nullable=False) # DUPLICATE_PAYMENT, MISSING_GST, UNMATCHED_LEDGER, FRAUD_FLAG
    severity = Column(String, nullable=False) # HIGH, MEDIUM, LOW
    description = Column(String, nullable=False)
    status = Column(String, default="OPEN") # OPEN, RESOLVED, IGNORED
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FinancialRule(Base):
    __tablename__ = "finance_rules"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String, nullable=False)
    rule_type = Column(String, nullable=False) # TAX, EXPENSE_LIMIT, VENDOR_APPROVAL
    parameters = Column(JSON, default={}) # e.g. {"max_meal_expense": 150}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
