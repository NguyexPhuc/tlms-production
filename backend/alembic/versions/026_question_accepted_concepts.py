"""add private accepted concepts for semantic question grading

Revision ID: 026_question_concepts
Revises: 025_baseline_reasoning_quiz
Create Date: 2026-10-15 22:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "026_question_concepts"
down_revision: Union[str, None] = "025_baseline_reasoning_quiz"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("accepted_concepts", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("questions", "accepted_concepts")
