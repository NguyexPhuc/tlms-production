"""enforce nine-digit student identifiers

Revision ID: 031_student_id_nine_digits
Revises: 030_local_auth_password
Create Date: 2026-11-13 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "031_student_id_nine_digits"
down_revision: Union[str, None] = "030_local_auth_password"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Invalid legacy/demo values cannot be used by LHU and are cleared before
    # the database-level constraint is enabled.
    op.execute(
        sa.text(
            """
            UPDATE users
            SET student_id = NULL, updated_at = now()
            WHERE student_id IS NOT NULL
              AND student_id !~ '^[0-9]{9}$'
            """
        )
    )
    op.create_check_constraint(
        "ck_users_student_id_nine_digits",
        "users",
        "student_id IS NULL OR student_id ~ '^[0-9]{9}$'",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_users_student_id_nine_digits",
        "users",
        type_="check",
    )
