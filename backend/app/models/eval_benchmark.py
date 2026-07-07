import uuid
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.base import Base


class EvalBenchmarkQuery(Base):
    __tablename__ = "eval_benchmark_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    query_text = Column(String, nullable=False)
    expected_doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    expected_page = Column(Integer, nullable=True)
    expected_answer_excerpt = Column(String, nullable=True)
    query_type = Column(String, nullable=False, default="human_reviewed")
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EvalResult(Base):
    __tablename__ = "eval_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    benchmark_query_id = Column(UUID(as_uuid=True), ForeignKey("eval_benchmark_queries.id", ondelete="SET NULL"), nullable=True, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    precision_at_5 = Column(Float, nullable=True)
    recall_at_5 = Column(Float, nullable=True)
    citation_correct = Column(Boolean, nullable=True)
    hallucination_detected = Column(Boolean, nullable=True)
    top_chunks_retrieved = Column(JSONB, nullable=True)
    grounded_answer_valid = Column(Boolean, nullable=True)
    reranker_delta = Column(Float, nullable=True)
    retrieval_latency_ms = Column(Integer, nullable=True)
    triggered_by = Column(String, nullable=False, default="manual")
    model_version = Column(String, nullable=True)
    chunking_version = Column(String, nullable=True)
    run_timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    notes = Column(String, nullable=True)
