"""add_session_tags

Phase 14.5: tags column on chat_sessions

Revision ID: 8b9c0d1e2f3a
Revises: 7a8b9c0d1e2f
Create Date: 2026-05-20 10:30:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "8b9c0d1e2f3a"
down_revision: Union[str, None] = "7a8b9c0d1e2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column("tags", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("chat_sessions", "tags")
