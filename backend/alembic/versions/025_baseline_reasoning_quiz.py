"""replace legacy baseline essays with objective reasoning quiz

Revision ID: 025_baseline_reasoning_quiz
Revises: 024_zalo_daily_quiz
Create Date: 2026-10-15 22:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "025_baseline_reasoning_quiz"
down_revision: Union[str, None] = "024_zalo_daily_quiz"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Preserve historical questions and answers while removing essay questions
    # from the active entry assessment. The service seeds the new five items.
    op.execute(
        sa.text(
            """
            UPDATE questions
            SET status = 'archived', is_baseline = false, updated_at = now()
            WHERE source = 'system'
              AND is_baseline = true
              AND question_type = 'short_answer'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE questions
            SET status = 'active', is_baseline = true, updated_at = now()
            WHERE source = 'system'
              AND category = 'baseline'
              AND question_type = 'short_answer'
            """
        )
    )
