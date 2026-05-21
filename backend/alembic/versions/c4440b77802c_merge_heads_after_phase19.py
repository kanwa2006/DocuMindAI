"""merge_heads_after_phase19

Revision ID: c4440b77802c
Revises: 87c96095e342, c2d3e4f5a6b7
Create Date: 2026-05-20 08:29:49.924833

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4440b77802c'
down_revision: Union[str, None] = ('87c96095e342', 'c2d3e4f5a6b7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
