"""add_email_notifications_enabled

Phase 17: adds email_notifications_enabled column to users table
to allow users to opt out of transactional lifecycle emails.

Revision ID: b1c2d3e4f5a6
Revises: 2245e3e6d30c
Create Date: 2026-05-20 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "2245e3e6d30c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "email_notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "email_notifications_enabled")
