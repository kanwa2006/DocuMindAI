"""merge_heads

Revision ID: 2a94679787a7
Revises: 6f7080910213, 9c0d1e2f3a4b
Create Date: 2026-05-20 03:33:57.692709

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a94679787a7'
down_revision: Union[str, None] = ('6f7080910213', '9c0d1e2f3a4b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
