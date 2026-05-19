from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class JobRoleCreate(BaseModel):
    title: str
    department: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[Dict[str, Any]] = None

class JobRoleResponse(BaseModel):
    id: UUID
    title: str
    department: Optional[str]
    description: Optional[str]
    requirements: Optional[Dict[str, Any]]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

VALID_STAGES = ["applied", "screened", "shortlisted", "interviewed", "offered", "hired", "rejected"]

class CandidateProfileResponse(BaseModel):
    id: UUID
    document_id: UUID
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    skills: List[str]
    experience_years: Optional[float]
    education: List[Dict[str, Any]]
    stage: Optional[str] = "applied"
    created_at: datetime

    class Config:
        from_attributes = True

class CandidateStageUpdate(BaseModel):
    stage: str

class JobMatchResponse(BaseModel):
    id: UUID
    job_id: UUID
    candidate_id: UUID
    fit_score: Optional[float]
    semantic_score: Optional[float] = None
    final_score: Optional[float] = None
    match_analysis: Optional[Dict[str, Any]]
    status: str
    recruiter_notes: Optional[str]

    class Config:
        from_attributes = True

class MatchScoreResponse(BaseModel):
    candidate_id: UUID
    match_id: UUID
    match_score: float
    skill_gaps: List[str]
    match_breakdown: Dict[str, Any]

class CandidateExtractionSchema(BaseModel):
    """Schema used by LLM to extract resume details"""
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = []
    experience_years: float = 0.0
    education: List[Dict[str, str]] = []
    certifications: List[str] = []
    summary: str

class MatchAnalysisSchema(BaseModel):
    """Schema used by LLM to score candidate against JD"""
    fit_score: float = Field(..., ge=0.0, le=100.0, description="Overall fit score from 0 to 100")
    pros: List[str] = Field(..., description="Reasons candidate is a good fit")
    cons: List[str] = Field(..., description="Reasons candidate might not be a fit")
    missing_skills: List[str] = Field(..., description="Skills from JD missing in resume")
    interview_questions: List[str] = Field(..., description="Suggested interview questions to probe gaps")

class CandidateNoteCreate(BaseModel):
    content: str
    
class CandidateNoteResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    author_id: UUID
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True
