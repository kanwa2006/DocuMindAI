"""resize document_chunks.embedding to 1024 dim for BAAI/bge-m3

The original column was Vector(384) for all-MiniLM-L6-v2 but the embedding
service now uses BAAI/bge-m3 which produces 1024-dim vectors. Every commit was
failing with `ValueError: expected 384 dimensions, not 1024`, which stuck every
upload in PROCESSING. Drop the HNSW index, alter the column, recreate the index.

Revision ID: a1b2c3d4e5f7
Revises: f2a3b4c5d6e7
Create Date: 2026-05-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # HNSW index is tied to the exact column type — drop, alter, recreate.
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding;")
    # No existing embeddings (verified: count = 0), so a straight USING NULL is safe.
    op.execute(
        "ALTER TABLE document_chunks "
        "ALTER COLUMN embedding TYPE vector(1024) USING NULL;"
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding;")
    op.execute(
        "ALTER TABLE document_chunks "
        "ALTER COLUMN embedding TYPE vector(384) USING NULL;"
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64);"
    )
