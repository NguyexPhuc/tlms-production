"""remove evening shift and update shift times

Revision ID: 011_update_shifts
Revises: 010_add_attendance_tracking
Create Date: 2026-03-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011_update_shifts'
down_revision: Union[str, None] = '010_add_attendance_tracking'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No database schema changes needed - just updating Python code
    # Shift enum is stored as strings in the database
    # Existing evening shifts will remain but won't be used for new registrations
    pass


def downgrade() -> None:
    pass
