"""merge_remaining_heads

Revision ID: 2245e3e6d30c
Revises: 2a94679787a7, a0b1c2d3e4f5
Create Date: 2026-05-20 04:01:39.375864

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2245e3e6d30c'
down_revision: Union[str, None] = ('2a94679787a7', 'a0b1c2d3e4f5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
