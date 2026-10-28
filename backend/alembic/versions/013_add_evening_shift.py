"""add evening_shift column to users table

Revision ID: 013_add_evening_shift
Revises: 012_add_creator_id
Create Date: 2026-04-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '013_add_evening_shift'
down_revision: Union[str, None] = '012_add_creator_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add evening_shift column
    op.add_column('users', sa.Column('evening_shift', sa.Boolean(), nullable=True, default=False))


def downgrade() -> None:
    # Remove evening_shift column
    op.drop_column('users', 'evening_shift')
