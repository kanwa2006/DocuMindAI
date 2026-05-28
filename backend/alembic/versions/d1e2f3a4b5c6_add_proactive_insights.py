"""add_proactive_insights

Phase 21: Proactive Intelligence Layer

Revision ID: d1e2f3a4b5c6
Revises: c4440b77802c
Create Date: 2026-05-20 12:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c4440b77802c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    exists = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='proactive_insights'"
        )
    ).fetchone()

    if not exists:
        op.create_table(
            "proactive_insights",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "document_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("documents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "session_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column("workspace", sa.String(50), nullable=False),
            sa.Column("insight_type", sa.String(100), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False),
            sa.Column("finding", sa.String(500), nullable=False),
            sa.Column("page_reference", sa.Integer, nullable=True),
            sa.Column("was_clicked", sa.Boolean, nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_proactive_insights_document_id", "proactive_insights", ["document_id"])
        op.create_index("ix_proactive_insights_session_id", "proactive_insights", ["session_id"])


def downgrade() -> None:
    conn = op.get_bind()

    ix_doc = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes WHERE schemaname='public' "
            "AND tablename='proactive_insights' AND indexname='ix_proactive_insights_document_id'"
        )
    ).fetchone()
    if ix_doc:
        op.drop_index("ix_proactive_insights_document_id", "proactive_insights")

    ix_sess = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes WHERE schemaname='public' "
            "AND tablename='proactive_insights' AND indexname='ix_proactive_insights_session_id'"
        )
    ).fetchone()
    if ix_sess:
        op.drop_index("ix_proactive_insights_session_id", "proactive_insights")

    tbl = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='proactive_insights'"
        )
    ).fetchone()
    if tbl:
        op.drop_table("proactive_insights")
