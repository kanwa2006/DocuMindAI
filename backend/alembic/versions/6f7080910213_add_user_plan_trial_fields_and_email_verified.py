"""add_user_plan_trial_fields_and_email_verified

Phase 10: adds plan, trial_queries_used, trial_started_at, subscribed_at,
subscription_ends_at, and email_verified to the users table.

Revision ID: 6f7080910213
Revises: 5e6f70809102
Create Date: 2026-05-19 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6f7080910213"
down_revision: Union[str, None] = "5e6f70809102"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("plan", sa.String(50), nullable=False, server_default="trial"),
    )
    op.add_column(
        "users",
        sa.Column("trial_queries_used", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column(
            "trial_started_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.add_column(
        "users",
        sa.Column("subscribed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("subscription_ends_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("users", "email_verified")
    op.drop_column("users", "subscription_ends_at")
    op.drop_column("users", "subscribed_at")
    op.drop_column("users", "trial_started_at")
    op.drop_column("users", "trial_queries_used")
    op.drop_column("users", "plan")
