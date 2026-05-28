"""add_vector_column

Revision ID: 314e3009bc29
Revises: 33229a9d2798
Create Date: 2026-05-14 23:14:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '314e3009bc29'
down_revision: Union[str, None] = '33229a9d2798'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.add_column('document_chunks', sa.Column('embedding', Vector(384), nullable=True))
    op.execute("CREATE INDEX ix_document_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);")

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding;")
    op.drop_column('document_chunks', 'embedding')
