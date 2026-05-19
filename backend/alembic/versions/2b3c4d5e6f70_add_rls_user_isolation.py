"""add_rls_user_isolation

Revision ID: 2b3c4d5e6f70
Revises: 1a2b3c4d5e60
Create Date: 2026-05-19 12:31:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = '2b3c4d5e6f70'
down_revision: Union[str, None] = '1a2b3c4d5e60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 9-C4: Owner-based RLS policy (defense-in-depth layer on top of existing workspace policy).
    # The primary guard is tenant_guard.py; RLS prevents direct DB-level leaks.
    # RLS is already enabled from migration e253f70b7e95 — only add the new policy.
    op.execute(
        """
        DROP POLICY IF EXISTS documents_user_isolation ON documents;
        CREATE POLICY documents_user_isolation ON documents
          USING (owner_id = current_setting('app.current_user_id', true)::uuid);
        """
    )
    # Organisation-scoped policy (enterprise mode — additive, does not break single-user deployments).
    op.execute(
        """
        DROP POLICY IF EXISTS documents_org_isolation ON documents;
        CREATE POLICY documents_org_isolation ON documents
          USING (
            current_setting('app.current_org_id', true) IS NOT NULL
            AND current_setting('app.current_org_id', true) != ''
          );
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS documents_user_isolation ON documents;")
    op.execute("DROP POLICY IF EXISTS documents_org_isolation ON documents;")
