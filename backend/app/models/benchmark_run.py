import uuid
from sqlalchemy import Column, String, DateTime, func, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String, nullable=False)
    
    # Aggregated metrics across all queries in the run
    mrr_before_rerank = Column(Float, nullable=True)
    mrr_after_rerank = Column(Float, nullable=True)
    avg_latency_sec = Column(Float, nullable=True)
    
    # Store individual query metric breakdowns
    results = Column(JSON, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
