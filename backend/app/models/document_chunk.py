import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy import Index
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    __table_args__ = (
        Index('ix_document_chunks_embedding', 'embedding', postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'}),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    page_id = Column(UUID(as_uuid=True), ForeignKey("document_pages.id", ondelete="CASCADE"), index=True, nullable=False)
    
    chunk_index = Column(Integer, nullable=False)
    text_content = Column(String, nullable=False)
    
    # Store semantic layout metadata (is_table, is_header, overlap_info)
    chunk_metadata = Column(JSON, nullable=True) 
    
    # 1024 dimensions for BAAI/bge-m3 (current embedding_service model).
    # If you change the embedding model, you MUST also alter this column dim and
    # the HNSW index, then re-embed every chunk.
    embedding = Column(Vector(1024), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
