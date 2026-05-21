"""repair_create_bookmarks

Repair: bookmarks table was not created by earlier migration run.
Creates table and index idempotently.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-05-20 14:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    exists = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='bookmarks'"
    )).fetchone()

    if not exists:
        op.create_table(
            "bookmarks",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("message_id", sa.String, nullable=False),
            sa.Column("message_content", sa.Text, nullable=False),
            sa.Column("citations", postgresql.JSON, nullable=True),
            sa.Column("tags", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
            sa.Column("workspace", sa.String, nullable=False, server_default="general"),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )

    ix_exists = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes "
        "WHERE schemaname='public' AND tablename='bookmarks' AND indexname='ix_bookmarks_user_id'"
    )).fetchone()
    if not ix_exists:
        op.create_index("ix_bookmarks_user_id", "bookmarks", ["user_id"])


def downgrade() -> None:
    conn = op.get_bind()
    ix_exists = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes "
        "WHERE schemaname='public' AND tablename='bookmarks' AND indexname='ix_bookmarks_user_id'"
    )).fetchone()
    if ix_exists:
        op.drop_index("ix_bookmarks_user_id", "bookmarks")

    exists = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='bookmarks'"
    )).fetchone()
    if exists:
        op.drop_table("bookmarks")
