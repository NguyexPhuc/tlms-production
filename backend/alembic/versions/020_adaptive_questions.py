"""adaptive question metadata and skill profiles

Revision ID: 020_adaptive_questions
Revises: 019_member_roadmaps
Create Date: 2026-09-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "020_adaptive_questions"
down_revision: Union[str, None] = "019_member_roadmaps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("topic", sa.String(length=120), nullable=True))
    op.add_column("questions", sa.Column("skill_key", sa.String(length=80), nullable=True))
    op.add_column("questions", sa.Column("question_type", sa.String(length=40), nullable=False, server_default="short_answer"))
    op.add_column("questions", sa.Column("numeric_difficulty", sa.Float(), nullable=False, server_default="3"))
    op.add_column("questions", sa.Column("source", sa.String(length=40), nullable=False, server_default="manager"))
    op.add_column("questions", sa.Column("learning_objective", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("is_baseline", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_index("ix_questions_skill_key", "questions", ["skill_key"])
    op.create_index("ix_questions_is_baseline", "questions", ["is_baseline"])

    op.add_column("user_question_answers", sa.Column("ai_confidence", sa.Float(), nullable=True))
    op.add_column("user_question_answers", sa.Column("ai_breakdown", sa.JSON(), nullable=True))
    op.add_column("user_question_answers", sa.Column("points_awarded", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "member_skill_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_key", sa.String(length=80), nullable=False),
        sa.Column("mastery_score", sa.Float(), nullable=False, server_default="50"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.3"),
        sa.Column("current_difficulty", sa.Float(), nullable=False, server_default="3"),
        sa.Column("attempts_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_score", sa.Float(), nullable=True),
        sa.Column("weak_topics", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("strong_topics", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("last_evaluated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "skill_key", name="uq_member_skill_profiles_user_skill"),
    )
    op.create_index("ix_member_skill_profiles_user_id", "member_skill_profiles", ["user_id"])
    op.create_index("ix_member_skill_profiles_skill_key", "member_skill_profiles", ["skill_key"])


def downgrade() -> None:
    op.drop_index("ix_member_skill_profiles_skill_key", table_name="member_skill_profiles")
    op.drop_index("ix_member_skill_profiles_user_id", table_name="member_skill_profiles")
    op.drop_table("member_skill_profiles")

    op.drop_column("user_question_answers", "points_awarded")
    op.drop_column("user_question_answers", "ai_breakdown")
    op.drop_column("user_question_answers", "ai_confidence")

    op.drop_index("ix_questions_is_baseline", table_name="questions")
    op.drop_index("ix_questions_skill_key", table_name="questions")
    op.drop_column("questions", "is_baseline")
    op.drop_column("questions", "learning_objective")
    op.drop_column("questions", "source")
    op.drop_column("questions", "numeric_difficulty")
    op.drop_column("questions", "question_type")
    op.drop_column("questions", "skill_key")
    op.drop_column("questions", "topic")
