"""add immutable adaptive research logging

Revision ID: 033_adaptive_research_logging
Revises: 032_user_avatar
Create Date: 2026-11-17 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "033_adaptive_research_logging"
down_revision: Union[str, None] = "032_user_avatar"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_participation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("study_code", sa.String(length=80), nullable=True),
        sa.Column("experiment_group", sa.String(length=20), nullable=False, server_default="NONE"),
        sa.Column("enrolled_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("consent_status", sa.String(length=20), nullable=False, server_default="NOT_REQUESTED"),
        sa.Column("data_origin", sa.String(length=20), nullable=False, server_default="UNKNOWN"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_research_participation_user_id"),
    )
    op.create_index("ix_research_participation_user_id", "research_participation", ["user_id"])

    op.create_table(
        "question_attempt_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("roadmap_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("roadmap_week", sa.Integer(), nullable=True),
        sa.Column("skill_key", sa.String(length=80), nullable=True),
        sa.Column("topic", sa.String(length=120), nullable=True),
        sa.Column("question_difficulty", sa.Float(), nullable=True),
        sa.Column("mastery_before", sa.Float(), nullable=True),
        sa.Column("difficulty_before", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("response_time_seconds", sa.Float(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("answer_snapshot", sa.Text(), nullable=False),
        sa.Column("question_title_snapshot", sa.String(length=255), nullable=False),
        sa.Column("question_text_snapshot", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("evaluation_method", sa.String(length=40), nullable=False),
        sa.Column("ai_score", sa.Float(), nullable=True),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("ai_provider", sa.String(length=40), nullable=True),
        sa.Column("ai_model", sa.String(length=120), nullable=True),
        sa.Column("prompt_version", sa.String(length=80), nullable=True),
        sa.Column("manager_score", sa.Float(), nullable=True),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("mastery_after", sa.Float(), nullable=True),
        sa.Column("difficulty_after", sa.Float(), nullable=True),
        sa.Column("adaptation_reason", sa.String(length=80), nullable=True),
        sa.Column("algorithm_version", sa.String(length=80), nullable=False),
        sa.Column("question_version", sa.String(length=80), nullable=True),
        sa.Column("data_origin", sa.String(length=20), nullable=False, server_default="UNKNOWN"),
        sa.Column("experiment_group", sa.String(length=20), nullable=False, server_default="NONE"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["roadmap_id"], ["member_roadmaps.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "user_id",
            "question_id",
            "attempt_number",
            name="uq_question_attempt_history_user_question_attempt",
        ),
    )
    op.create_index("ix_question_attempt_history_user_id", "question_attempt_history", ["user_id"])
    op.create_index("ix_question_attempt_history_question_id", "question_attempt_history", ["question_id"])
    op.create_index("ix_question_attempt_history_created_at", "question_attempt_history", ["created_at"])

    op.create_table(
        "skill_mastery_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_key", sa.String(length=80), nullable=False),
        sa.Column("mastery_before", sa.Float(), nullable=True),
        sa.Column("mastery_after", sa.Float(), nullable=True),
        sa.Column("confidence_before", sa.Float(), nullable=True),
        sa.Column("confidence_after", sa.Float(), nullable=True),
        sa.Column("difficulty_before", sa.Float(), nullable=True),
        sa.Column("difficulty_after", sa.Float(), nullable=True),
        sa.Column("trigger_type", sa.String(length=40), nullable=False),
        sa.Column("trigger_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("algorithm_version", sa.String(length=80), nullable=False),
        sa.Column("data_origin", sa.String(length=20), nullable=False, server_default="UNKNOWN"),
        sa.Column("experiment_group", sa.String(length=20), nullable=False, server_default="NONE"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trigger_id"], ["question_attempt_history.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_skill_mastery_history_user_skill", "skill_mastery_history", ["user_id", "skill_key"])
    op.create_index("ix_skill_mastery_history_created_at", "skill_mastery_history", ["created_at"])

    op.create_table(
        "question_serve_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("attempt_history_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("data_origin", sa.String(length=20), nullable=False, server_default="UNKNOWN"),
        sa.Column("experiment_group", sa.String(length=20), nullable=False, server_default="NONE"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["attempt_history_id"], ["question_attempt_history.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_question_serve_sessions_user_question", "question_serve_sessions", ["user_id", "question_id"])
    op.create_index(
        "uq_question_serve_sessions_active",
        "question_serve_sessions",
        ["user_id", "question_id"],
        unique=True,
        postgresql_where=sa.text("consumed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_question_serve_sessions_active", table_name="question_serve_sessions")
    op.drop_index("ix_question_serve_sessions_user_question", table_name="question_serve_sessions")
    op.drop_table("question_serve_sessions")
    op.drop_index("ix_skill_mastery_history_created_at", table_name="skill_mastery_history")
    op.drop_index("ix_skill_mastery_history_user_skill", table_name="skill_mastery_history")
    op.drop_table("skill_mastery_history")
    op.drop_index("ix_question_attempt_history_created_at", table_name="question_attempt_history")
    op.drop_index("ix_question_attempt_history_question_id", table_name="question_attempt_history")
    op.drop_index("ix_question_attempt_history_user_id", table_name="question_attempt_history")
    op.drop_table("question_attempt_history")
    op.drop_index("ix_research_participation_user_id", table_name="research_participation")
    op.drop_table("research_participation")
