"""add_bookmarks_notifications

Phase 14.4: bookmarks table
Phase 14.7: notifications table

Revision ID: 7a8b9c0d1e2f
Revises: 5e6f70809102
Create Date: 2026-05-20 10:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "7a8b9c0d1e2f"
down_revision: Union[str, None] = "5e6f70809102"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── notifications ──────────────────────────────────────────────────────────
    # Table may already exist from 4d5e6f708091_add_retention_report_tables
    notifications_exists = conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='notifications'")
    ).fetchone()
    if not notifications_exists:
        op.create_table(
            "notifications",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("type", sa.String, nullable=False, server_default="system"),
            sa.Column("title", sa.String, nullable=False),
            sa.Column("body", sa.Text, nullable=True),
            sa.Column("action_url", sa.String, nullable=True),
            sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )

    ix_notif_exists = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE schemaname='public' AND tablename='notifications' AND indexname='ix_notifications_user_id'")
    ).fetchone()
    if not ix_notif_exists:
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    # ── bookmarks ──────────────────────────────────────────────────────────────
    bookmarks_exists = conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='bookmarks'")
    ).fetchone()
    if not bookmarks_exists:
        op.create_table(
            "bookmarks",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("message_id", sa.String, nullable=False),
            sa.Column("message_content", sa.Text, nullable=False),
            sa.Column("citations", postgresql.JSON, nullable=True),
            sa.Column("tags", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
            sa.Column("workspace", sa.String, nullable=False, server_default="general"),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )

    ix_bm_exists = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE schemaname='public' AND tablename='bookmarks' AND indexname='ix_bookmarks_user_id'")
    ).fetchone()
    if not ix_bm_exists:
        op.create_index("ix_bookmarks_user_id", "bookmarks", ["user_id"])


def downgrade() -> None:
    conn = op.get_bind()

    # Only drop bookmarks — this migration owns it
    bm_idx_exists = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE schemaname='public' AND tablename='bookmarks' AND indexname='ix_bookmarks_user_id'")
    ).fetchone()
    if bm_idx_exists:
        op.drop_index("ix_bookmarks_user_id", "bookmarks")

    bm_exists = conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='bookmarks'")
    ).fetchone()
    if bm_exists:
        op.drop_table("bookmarks")

    # notifications pre-existed in 4d5e6f708091; only drop the index added here
    # if that earlier migration did not already create it
    notif_idx_exists = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE schemaname='public' AND tablename='notifications' AND indexname='ix_notifications_user_id'")
    ).fetchone()
    # The earlier migration also created ix_notifications_user_id, so leave it alone
