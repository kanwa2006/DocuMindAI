from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class ComplianceRuleCreate(BaseModel):
    name: str
    category: str
    rule_description: str
    mandatory: bool = False

class ComplianceRuleResponse(BaseModel):
    id: UUID
    name: str
    category: str
    rule_description: str
    mandatory: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class ContractResponse(BaseModel):
    id: UUID
    document_id: UUID
    title: str
    party_name: Optional[str]
    contract_type: Optional[str]
    status: str
    risk_score: Optional[str]
    metadata_json: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- LLM Generation Schemas ---

class ExtractedClauseSchema(BaseModel):
    """Schema for LLM to strictly segment a contract into structural clauses."""
    section_name: str = Field(..., description="The heading or section name (e.g., '3. Confidentiality')")
    clause_type: str = Field(..., description="Semantic type (e.g., INDEMNITY, PAYMENT, TERMINATION)")
    original_text: str = Field(..., description="The verbatim text of the clause")

class ContractSegmentationSchema(BaseModel):
    contract_type: str
    party_name: str
    clauses: List[ExtractedClauseSchema]

class ClauseComplianceSchema(BaseModel):
    """Schema for LLM to strictly evaluate a clause against a rule."""
    is_compliant: bool = Field(..., description="Does the clause strictly adhere to the compliance rule?")
    risk_level: str = Field(..., description="HIGH, MEDIUM, LOW, or COMPLIANT")
    compliance_notes: str = Field(..., description="Explanation of the risk or adherence")
    needs_redline: bool = Field(..., description="True if the clause requires legal redlining")
    suggested_redline_text: Optional[str] = Field(None, description="Safer legal text replacing the risky text")
