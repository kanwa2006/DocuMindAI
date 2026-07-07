from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class BenchmarkQueryDefinition(BaseModel):
    query: str
    expected_document_ids: List[UUID]
    expected_chunk_ids: Optional[List[UUID]] = None

class BenchmarkRunCreate(BaseModel):
    name: str
    queries: List[BenchmarkQueryDefinition]
    
class BenchmarkRunResponse(BaseModel):
    id: UUID
    name: str
    mrr_before_rerank: float
    mrr_after_rerank: float
    avg_latency_sec: float
    results: List[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True
