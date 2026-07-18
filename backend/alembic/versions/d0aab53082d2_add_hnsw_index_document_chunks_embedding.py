"""add_hnsw_index_document_chunks_embedding

H-1: VECTOR_BACKEND now defaults to pgvector, whose semantic branch orders
by DocumentChunk.embedding.cosine_distance(). Without an ANN index every
query is an exact scan. HNSW (pgvector >= 0.5.0; the project pins
ankane/pgvector:v0.5.1) with vector_cosine_ops matches the cosine operator
used in retrieval_service. Built CONCURRENTLY (autocommit block) so an
existing corpus is not locked during the build.

Revision ID: d0aab53082d2
Revises: ef358fcc72ac
Create Date: 2026-07-18 17:17:29.656567

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0aab53082d2'
down_revision: Union[str, None] = 'ef358fcc72ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "ix_document_chunks_embedding_hnsw"


def upgrade() -> None:
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
    with op.get_context().autocommit_block():
        op.execute(
            f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {INDEX_NAME} "
            "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {INDEX_NAME}")
