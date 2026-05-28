"""add_retention_report_tables

Phase 9-E: saved_query_templates, notifications, scheduled_reports
Phase 9-F: report_shares, message_notes

Revision ID: 4d5e6f708091
Revises: 3c4d5e6f7080
Create Date: 2026-05-19 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "4d5e6f708091"
down_revision: Union[str, None] = "3c4d5e6f7080"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Phase 9-E: Workflow Retention ─────────────────────────────────────────

    op.create_table(
        "saved_query_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("query_text", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_sqt_user_id", "saved_query_templates", ["user_id"])
    op.create_index("ix_sqt_use_count", "saved_query_templates", ["use_count"])

    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("link", sa.String(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
    op.create_index(
        "ix_notifications_user_unread",
        "notifications",
        ["user_id", "is_read"],
    )

    op.create_table(
        "scheduled_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("frequency", sa.String(), nullable=False, server_default="weekly"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_scheduled_reports_user_id", "scheduled_reports", ["user_id"])
    op.create_index("ix_scheduled_reports_session_id", "scheduled_reports", ["session_id"])
    op.create_index(
        "ix_scheduled_reports_next_run",
        "scheduled_reports",
        ["next_run_at", "is_active"],
    )

    # ── Phase 9-F: Distribution ───────────────────────────────────────────────

    op.create_table(
        "report_shares",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("share_token", sa.String(), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("watermark_text", sa.String(), nullable=True),
        sa.Column("report_config", JSONB(), nullable=True),
        sa.Column("report_pdf_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_report_shares_share_token", "report_shares", ["share_token"], unique=True)
    op.create_index("ix_report_shares_user_created", "report_shares", ["user_id", "created_at"])
    op.create_index("ix_report_shares_session_id", "report_shares", ["session_id"])

    op.create_table(
        "message_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "message_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("note_text", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_message_notes_message_id", "message_notes", ["message_id"])
    op.create_index("ix_message_notes_user_id", "message_notes", ["user_id"])


def downgrade() -> None:
    op.drop_table("message_notes")
    op.drop_table("report_shares")
    op.drop_table("scheduled_reports")
    op.drop_table("notifications")
    op.drop_table("saved_query_templates")
