"""merge orphaned migration head

Revision ID: ef358fcc72ac
Revises: a1b2c3d4e5f7, a9b8c7d6e5f4
Create Date: 2026-07-04 01:40:38.924181

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef358fcc72ac'
down_revision: Union[str, None] = ('a1b2c3d4e5f7', 'a9b8c7d6e5f4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
