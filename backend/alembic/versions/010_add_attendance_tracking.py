"""add attendance tracking columns to users table

Revision ID: 010_add_attendance_tracking
Revises: 009_add_phone_column
Create Date: 2026-03-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010_add_attendance_tracking'
down_revision: Union[str, None] = '009_add_phone_column'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add attendance tracking columns
    op.add_column('users', sa.Column('last_attendance_date', sa.String(10), nullable=True))
    op.add_column('users', sa.Column('morning_shift', sa.Boolean(), nullable=True, default=False))
    op.add_column('users', sa.Column('afternoon_shift', sa.Boolean(), nullable=True, default=False))
    op.add_column('users', sa.Column('is_late_today', sa.Boolean(), nullable=True, default=False))


def downgrade() -> None:
    # Remove attendance tracking columns
    op.drop_column('users', 'is_late_today')
    op.drop_column('users', 'afternoon_shift')
    op.drop_column('users', 'morning_shift')
    op.drop_column('users', 'last_attendance_date')
