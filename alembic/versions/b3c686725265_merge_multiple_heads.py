"""Merge multiple heads

Revision ID: b3c686725265
Revises: 51c903151a82, 99311c02d230
Create Date: 2025-04-07 21:02:37.264950

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c686725265'
down_revision: Union[str, None] = ('51c903151a82', '99311c02d230')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
