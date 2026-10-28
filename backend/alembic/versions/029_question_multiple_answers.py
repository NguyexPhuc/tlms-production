"""support multiple correct options in the shared question bank

Revision ID: 029_question_multiple_answers
Revises: 028_course_enrollments
Create Date: 2026-10-27 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "029_question_multiple_answers"
down_revision: Union[str, None] = "028_course_enrollments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("correct_options", sa.JSON(), nullable=True))
    op.execute("""
        UPDATE questions
        SET correct_options = json_build_array(upper(correct_option))
        WHERE correct_option IS NOT NULL AND correct_options IS NULL
    """)


def downgrade() -> None:
    op.drop_column("questions", "correct_options")
