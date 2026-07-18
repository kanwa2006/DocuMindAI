"""resize_domain_embeddings_to_1024

C-7 (newly discovered during H-4): every workspace embedding column was
created as vector(1536) (an OpenAI-ada-era scaffold) while the actual
embedding pipeline (embedding_service, bge-m3) produces 1024-dim vectors.
Even after C-1/C-2, inserts and l2_distance comparisons would fail with a
dimension mismatch. Same class of bug — and same fix — as
a1b2c3d4e5f7_resize_chunk_embedding_to_1024.

USING NULL is safe here: both writer paths (worker tasks + get_embedding)
were broken since inception, so these columns cannot contain real data in
any deployment that ran this codebase.

Revision ID: 2a2aee1828d4
Revises: d0aab53082d2
Create Date: 2026-07-18 17:28:34.628235

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a2aee1828d4'
down_revision: Union[str, None] = 'd0aab53082d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, column) pairs declared vector(1536) but fed 1024-dim vectors
_COLUMNS = [
    ("hr_candidates", "embedding"),
    ("legal_clauses", "embedding"),
    ("finance_transactions", "embedding"),
    ("study_notes", "embedding"),
    ("study_flashcards", "embedding"),
    ("research_papers", "embedding"),
    ("research_findings", "embedding"),
]


def upgrade() -> None:
    for table, column in _COLUMNS:
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {column} TYPE vector(1024) USING NULL;"
        )


def downgrade() -> None:
    for table, column in _COLUMNS:
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {column} TYPE vector(1536) USING NULL;"
        )
