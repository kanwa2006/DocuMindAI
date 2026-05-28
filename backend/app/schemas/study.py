from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class FlashcardGenerationSchema(BaseModel):
    front: str = Field(..., description="The question or concept prompt")
    back: str = Field(..., description="The detailed answer or explanation")
    citation: Optional[str] = Field(None, description="Exact quote or reference from the source document to ground the answer")
    difficulty: str = Field(..., description="EASY, MEDIUM, or HARD")

class NoteGenerationSchema(BaseModel):
    title: str = Field(..., description="A concise title for the extracted concept")
    content: str = Field(..., description="Detailed explanation of the concept")
    tags: List[str] = Field(default=[], description="Keywords associated with the concept")
    flashcards: List[FlashcardGenerationSchema] = Field(default=[], description="Generated flashcards for this concept")

class DocumentStudyExtractionSchema(BaseModel):
    """Schema for parsing an entire document into atomic study components."""
    document_summary: str = Field(..., description="High-level summary of the entire document")
    notes: List[NoteGenerationSchema] = Field(default=[], description="Key concepts extracted as notes")

class FlashcardResponse(BaseModel):
    id: UUID
    deck_id: UUID
    front: str
    back: str
    citation: Optional[str]
    next_review_date: datetime
    
    class Config:
        from_attributes = True

class DeckResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    
    class Config:
        from_attributes = True
