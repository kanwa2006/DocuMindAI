from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID

class QueryRequest(BaseModel):
    query: str
    workspace_id: Optional[UUID] = None
    session_id: Optional[str] = None       # for conversation history lookup
    workspace_type: Optional[str] = "general"  # for retrieval config + disclaimers
    top_k: int = 5
    similarity_threshold: float = 0.0
    comparison_mode: bool = False          # Phase 14.6: multi-doc comparison

class EvidenceChunk(BaseModel):
    chunk_id: UUID
    document_id: UUID
    filename: str
    page_number: int
    text_content: str
    similarity_score: Optional[float] = None
    rerank_score: Optional[float] = None
    layout_metadata: Optional[Dict[str, Any]] = None

class TracingDiagnostics(BaseModel):
    embedding_time_sec: float = 0.0
    database_time_sec: float = 0.0
    reranking_time_sec: float = 0.0
    generation_time_sec: float = 0.0
    total_time_sec: float = 0.0
    candidates_retrieved: int = 0
    evidence_accepted: int = 0
    estimated_tokens: int = 0

class QueryResponse(BaseModel):
    query: str
    answer: str
    confidence_score: float
    evidence: List[EvidenceChunk]
    diagnostics: TracingDiagnostics
