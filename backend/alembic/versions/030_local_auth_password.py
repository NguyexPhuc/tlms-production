"""add optional local password hash

Revision ID: 030_local_auth_password
Revises: 029_question_multiple_answers
Create Date: 2026-11-12 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "030_local_auth_password"
down_revision: Union[str, None] = "029_question_multiple_answers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
