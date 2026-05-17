from pydantic import BaseModel, Field, root_validator, model_validator
from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid
from datetime import datetime

class SubQuestionSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    text: str
    marks: float
    answer_key: Optional[str] = None
    rubric: Optional[str] = None

class QuestionSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    marks: float
    difficulty: Optional[str] = "medium"
    bloom_taxonomy: Optional[str] = None
    co_po_mapping: Optional[str] = None
    topic: Optional[str] = None
    sub_questions: List[SubQuestionSchema] = []
    answer_key: Optional[str] = None
    rubric: Optional[str] = None

class SectionSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    instructions: Optional[str] = None
    questions: List[QuestionSchema] = []

class ExamPaperContent(BaseModel):
    sections: List[SectionSchema] = []

    @model_validator(mode='after')
    def validate_marks(self) -> 'ExamPaperContent':
        for section in self.sections:
            for q in section.questions:
                if q.sub_questions:
                    sub_total = sum(sq.marks for sq in q.sub_questions)
                    if abs(sub_total - q.marks) > 0.001:
                        raise ValueError(f"Question '{q.text[:20]}...' total marks ({q.marks}) does not match sum of sub-questions ({sub_total})")
        return self

class ExamPaperCreate(BaseModel):
    title: str
    description: Optional[str] = None
    content: ExamPaperContent

class ExamPaperUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[ExamPaperContent] = None
    status: Optional[str] = None
    save_version: bool = False
    version_tag: Optional[str] = None

class ExamPaperResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    content: ExamPaperContent
    status: str
    share_token: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class GenerateQuestionRequest(BaseModel):
    topic: str
    difficulty: str = "medium"
    bloom_taxonomy: Optional[str] = None
    marks: float = 1.0
    document_ids: Optional[List[UUID]] = None
