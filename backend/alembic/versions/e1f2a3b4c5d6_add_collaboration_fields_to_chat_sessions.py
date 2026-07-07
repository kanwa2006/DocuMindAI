"""add_collaboration_fields_to_chat_sessions

Phase 22: Collaboration Layer — adds sharing fields to chat_sessions.

Revision ID: e1f2a3b4c5d6
Revises: d1e2f3a4b5c6
Create Date: 2026-05-20 14:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    existing = {
        row[0]
        for row in conn.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='chat_sessions'"
            )
        )
    }

    if "is_shared" not in existing:
        op.add_column("chat_sessions", sa.Column("is_shared", sa.Boolean(), nullable=False, server_default="false"))
    if "share_token" not in existing:
        op.add_column("chat_sessions", sa.Column("share_token", sa.String(32), nullable=True))
        op.create_unique_constraint("uq_chat_sessions_share_token", "chat_sessions", ["share_token"])
    if "share_permissions" not in existing:
        op.add_column("chat_sessions", sa.Column("share_permissions", sa.String(20), nullable=False, server_default="view_and_ask"))
    if "shared_at" not in existing:
        op.add_column("chat_sessions", sa.Column("shared_at", sa.DateTime(), nullable=True))
    if "max_collaborators" not in existing:
        op.add_column("chat_sessions", sa.Column("max_collaborators", sa.Integer(), nullable=False, server_default="5"))


def downgrade() -> None:
    conn = op.get_bind()

    existing = {
        row[0]
        for row in conn.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='chat_sessions'"
            )
        )
    }

    constraints = {
        row[0]
        for row in conn.execute(
            sa.text(
                "SELECT constraint_name FROM information_schema.table_constraints "
                "WHERE table_schema='public' AND table_name='chat_sessions'"
            )
        )
    }

    if "uq_chat_sessions_share_token" in constraints:
        op.drop_constraint("uq_chat_sessions_share_token", "chat_sessions", type_="unique")

    for col in ("is_shared", "share_token", "share_permissions", "shared_at", "max_collaborators"):
        if col in existing:
            op.drop_column("chat_sessions", col)
