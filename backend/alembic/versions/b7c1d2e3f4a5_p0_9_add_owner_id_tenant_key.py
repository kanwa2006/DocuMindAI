"""P0-9: add owner_id tenant key to legal/finance/study/research tables

Every one of these 18 tables carried only `workspace_id`, which is derived from
a workspace SLUG (`uuid5(NAMESPACE_DNS, "legal"|"finance"|...)`) and is
therefore IDENTICAL for every user in the system. It partitions rows by
category, not by tenant, so queries filtering on it alone returned every
user's rows. The documented invariant ("filter on owner_id AND the workspace
UUID") was not merely omitted at the call sites — with no ownership column it
was unrepresentable.

All 18 tables were verified EMPTY at the time this migration was written, so
the column is added NOT NULL directly with no backfill. If that is ever untrue
in another environment, this migration will fail loudly on the NOT NULL
constraint rather than silently assigning rows to the wrong tenant — which is
the correct failure mode for a tenant-isolation fix.

Revision ID: b7c1d2e3f4a5
Revises: 2a2aee1828d4
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "b7c1d2e3f4a5"
down_revision: Union[str, None] = "2a2aee1828d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES: tuple[str, ...] = (
    # Legal
    "legal_contracts",
    "legal_compliance_rules",
    "legal_clauses",
    "legal_redlines",
    "legal_approvals",
    # Finance
    "finance_documents",
    "finance_transactions",
    "finance_audit_findings",
    "finance_rules",
    # Study
    "study_notes",
    "study_flashcard_decks",
    "study_flashcards",
    "study_quizzes",
    "study_quiz_attempts",
    # Research
    "research_projects",
    "research_papers",
    "research_findings",
    "research_contradictions",
)


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column("owner_id", UUID(as_uuid=True), nullable=False),
        )
        # Indexed because owner_id is now in the WHERE clause of every query
        # against these tables. The composite ordering (owner_id, workspace_id)
        # matches the filter order in the endpoints.
        op.create_index(
            f"ix_{table}_owner_id",
            table,
            ["owner_id"],
        )
        op.create_index(
            f"ix_{table}_owner_workspace",
            table,
            ["owner_id", "workspace_id"],
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_index(f"ix_{table}_owner_workspace", table_name=table)
        op.drop_index(f"ix_{table}_owner_id", table_name=table)
        op.drop_column(table, "owner_id")
