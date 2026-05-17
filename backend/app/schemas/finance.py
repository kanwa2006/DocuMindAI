from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class TransactionSchema(BaseModel):
    date: Optional[str] = Field(None, description="Transaction date in ISO format")
    description: str = Field(..., description="Line item or transaction description")
    amount: float = Field(..., description="Absolute monetary amount")
    currency: str = Field("USD", description="Currency code (e.g., USD, EUR, INR)")
    category: Optional[str] = Field(None, description="Expense or accounting category")

class InvoiceExtractionSchema(BaseModel):
    """Schema for LLM to strictly extract invoice data into structured JSON."""
    doc_type: str = Field(..., description="INVOICE, RECEIPT, OR CREDIT_NOTE")
    vendor_name: Optional[str] = Field(None, description="Name of the billing entity")
    total_amount: Optional[float] = Field(None, description="Total amount due or paid")
    currency: Optional[str] = Field("USD", description="Currency code")
    tax_amount: Optional[float] = Field(None, description="Total tax, VAT, or GST amount")
    invoice_date: Optional[str] = Field(None, description="Date of the invoice")
    line_items: List[TransactionSchema] = Field(default=[], description="Individual items billed")

class AnomalyDetectionSchema(BaseModel):
    """Schema for deterministic or LLM-based audit rules."""
    is_anomaly: bool = Field(..., description="Does this transaction violate audit policies?")
    finding_type: Optional[str] = Field(None, description="DUPLICATE, MISSING_TAX, ROUNDING_FRAUD, LIMIT_EXCEEDED")
    severity: Optional[str] = Field(None, description="HIGH, MEDIUM, LOW")
    reason: Optional[str] = Field(None, description="Explanation of the anomaly")

class FinancialDocumentResponse(BaseModel):
    id: UUID
    document_id: UUID
    doc_type: str
    vendor_name: Optional[str]
    total_amount: Optional[float]
    currency: Optional[str]
    status: str
    extracted_data: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True

class AuditFindingResponse(BaseModel):
    id: UUID
    financial_doc_id: Optional[UUID]
    transaction_id: Optional[UUID]
    finding_type: str
    severity: str
    description: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True
