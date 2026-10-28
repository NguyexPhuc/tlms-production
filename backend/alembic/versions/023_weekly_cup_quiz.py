"""weekly cup quiz attempts

Revision ID: 023_weekly_cup_quiz
Revises: 022_weekly_cups
Create Date: 2026-10-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "023_weekly_cup_quiz"
down_revision: Union[str, None] = "022_weekly_cups"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "weekly_cup_events",
        sa.Column("questions", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )

    op.create_table(
        "weekly_cup_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("total_questions", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["event_id"], ["weekly_cup_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("event_id", "user_id", name="uq_weekly_cup_attempts_event_user"),
    )
    op.create_index("ix_weekly_cup_attempts_event_id", "weekly_cup_attempts", ["event_id"])
    op.create_index("ix_weekly_cup_attempts_user_id", "weekly_cup_attempts", ["user_id"])
    op.create_index("ix_weekly_cup_attempts_score_duration", "weekly_cup_attempts", ["score", "duration_seconds"])


def downgrade() -> None:
    op.drop_index("ix_weekly_cup_attempts_score_duration", table_name="weekly_cup_attempts")
    op.drop_index("ix_weekly_cup_attempts_user_id", table_name="weekly_cup_attempts")
    op.drop_index("ix_weekly_cup_attempts_event_id", table_name="weekly_cup_attempts")
    op.drop_table("weekly_cup_attempts")
    op.drop_column("weekly_cup_events", "questions")
