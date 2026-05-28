"""enable_rls_documents

Revision ID: e253f70b7e95
Revises: 14f40b0065e4
Create Date: 2026-05-14 22:02:42.851289

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e253f70b7e95'
down_revision: Union[str, None] = '14f40b0065e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PHASE 4: POSTGRES ROW-LEVEL SECURITY
    op.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON documents;")
    op.execute("CREATE POLICY tenant_isolation_policy ON documents USING (workspace_id::text = current_setting('app.current_workspace_id', true));")

def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON documents;")
    op.execute("ALTER TABLE documents DISABLE ROW LEVEL SECURITY;")
