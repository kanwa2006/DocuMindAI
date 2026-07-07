"""make document workspace_id not null

Revision ID: a9b8c7d6e5f4
Revises: 2245e3e6d30c
Create Date: 2026-05-28 00:00:00.000000

Backfills NULL workspace_id rows to 'general' (deterministic UUID5 slug)
before adding the NOT NULL constraint, so existing data is preserved.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'a9b8c7d6e5f4'
down_revision = '2245e3e6d30c'
branch_labels = None
depends_on = None

# UUID5(NAMESPACE_DNS, "general") — same derivation as resolve_workspace_id()
GENERAL_WORKSPACE_UUID = 'f8b4e6d2-4a3c-5b9e-8f1d-2e6a7c0b3d5e'


def upgrade() -> None:
    # 1. Backfill NULL workspace_id values to the 'general' workspace UUID
    op.execute(
        f"UPDATE documents SET workspace_id = '{GENERAL_WORKSPACE_UUID}'::uuid "
        f"WHERE workspace_id IS NULL"
    )
    # 2. Add NOT NULL constraint now that there are no NULLs
    op.alter_column(
        'documents',
        'workspace_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )


def downgrade() -> None:
    # Revert to nullable (no data loss — NULLs were already gone)
    op.alter_column(
        'documents',
        'workspace_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
