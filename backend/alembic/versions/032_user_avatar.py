"""add user avatar URL

Revision ID: 032_user_avatar
Revises: 031_student_id_nine_digits
Create Date: 2026-11-13 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "032_user_avatar"
down_revision: Union[str, None] = "031_student_id_nine_digits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
