"""add_display_name_gin_index

Phase 9-G1: documents.display_name column (user-visible label, nullable)
Phase 9-G4: GIN index on legal_analyses.clause_risks for cross-session clause search

Revision ID: 5e6f70809102
Revises: 4d5e6f708091
Create Date: 2026-05-19 13:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5e6f70809102"
down_revision: Union[str, None] = "4d5e6f708091"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Phase 9-G1: optional human-readable name for a document
    op.add_column(
        "documents",
        sa.Column("display_name", sa.String(50), nullable=True),
    )

    # Phase 9-G4: GIN index on legal_analyses.clause_risks for fast JSONB full-text search.
    # Guarded: table may not exist in all environments.
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'legal_analyses'
          ) THEN
            CREATE INDEX IF NOT EXISTS idx_legal_analyses_clause_risks_gin
            ON legal_analyses USING GIN (clause_risks);
          END IF;
        END $$
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS idx_legal_analyses_clause_risks_gin"
    )
    op.drop_column("documents", "display_name")
