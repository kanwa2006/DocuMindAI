"""add_extracted_to_enum

Revision ID: 8bb564faf40b
Revises: 72177cce8149
Create Date: 2026-05-14 17:36:52.433443

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bb564faf40b'
down_revision: Union[str, None] = '72177cce8149'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE documentstatus ADD VALUE IF NOT EXISTS 'EXTRACTED'")


def downgrade() -> None:
    pass
