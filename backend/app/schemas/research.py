from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class AuthorSchema(BaseModel):
    name: str

class FindingExtractionSchema(BaseModel):
    statement: str = Field(..., description="The core conclusion or finding")
    evidence_quote: str = Field(..., description="Exact quote supporting the finding")
    methodology: str = Field(..., description="Method used to derive this finding")

class PaperExtractionSchema(BaseModel):
    title: str = Field(..., description="Title of the research paper")
    authors: List[str] = Field(..., description="List of author names")
    abstract: str = Field(..., description="Abstract or summary of the paper")
    published_year: Optional[str] = Field(None, description="Year of publication")
    findings: List[FindingExtractionSchema] = Field(..., description="Key findings extracted from the text")

class ContradictionSchema(BaseModel):
    description: str = Field(..., description="Description of why these two findings conflict")

class SynthesisRequestSchema(BaseModel):
    project_id: UUID
