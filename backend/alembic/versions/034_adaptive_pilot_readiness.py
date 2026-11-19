"""complete adaptive research pilot logging

Revision ID: 034_adaptive_pilot_readiness
Revises: 033_adaptive_research_logging
Create Date: 2026-11-17 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "034_adaptive_pilot_readiness"
down_revision: Union[str, None] = "033_adaptive_research_logging"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE research_participant_code_seq START WITH 1")
    op.add_column(
        "research_participation",
        sa.Column(
            "participant_code",
            sa.String(length=20),
            nullable=True,
            server_default=sa.text(
                "'P' || to_char(nextval('research_participant_code_seq'), 'FM000000')"
            ),
        ),
    )
    # Existing enrollments get a deterministic one-time assignment. Future
    # enrollments use the sequence and never regenerate their code at export.
    op.execute(
        """
        WITH ordered AS (
            SELECT id, row_number() OVER (ORDER BY created_at, id) AS code_number
            FROM research_participation
        )
        UPDATE research_participation AS participation
        SET participant_code = 'P' || to_char(ordered.code_number, 'FM000000')
        FROM ordered
        WHERE participation.id = ordered.id
        """
    )
    op.execute(
        """
        SELECT setval(
            'research_participant_code_seq',
            GREATEST((SELECT count(*) FROM research_participation), 1),
            (SELECT count(*) > 0 FROM research_participation)
        )
        """
    )
    op.alter_column("research_participation", "participant_code", nullable=False)
    op.create_unique_constraint(
        "uq_research_participation_participant_code",
        "research_participation",
        ["participant_code"],
    )

    op.add_column("questions", sa.Column("source_name", sa.String(length=160), nullable=True))
    op.add_column("questions", sa.Column("source_url", sa.String(length=1000), nullable=True))
    op.add_column("questions", sa.Column("source_license", sa.String(length=120), nullable=True))
    op.add_column("questions", sa.Column("is_original", sa.Boolean(), nullable=True))
    op.add_column("questions", sa.Column("is_adapted", sa.Boolean(), nullable=True))
    op.add_column("questions", sa.Column("parent_question_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "questions",
        sa.Column("verified_status", sa.String(length=20), nullable=False, server_default="UNVERIFIED"),
    )
    op.add_column("questions", sa.Column("verified_by_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("questions", sa.Column("verified_at", sa.DateTime(), nullable=True))
    op.create_foreign_key(
        "fk_questions_parent_question_id",
        "questions",
        "questions",
        ["parent_question_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_questions_verified_by_id",
        "questions",
        "users",
        ["verified_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    for name, column_type in (
        ("recent_accuracy", sa.Float()),
        ("recent_avg_score", sa.Float()),
        ("recent_attempts", sa.Integer()),
        ("recent_response_time_seconds", sa.Float()),
        ("recent_window_size", sa.Integer()),
        ("response_time_status", sa.String(length=30)),
    ):
        op.add_column("question_attempt_history", sa.Column(name, column_type, nullable=True))

    op.create_table(
        "adaptive_decision_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_code", sa.String(length=20), nullable=True),
        sa.Column("skill_key", sa.String(length=80), nullable=True),
        sa.Column("topic", sa.String(length=120), nullable=True),
        sa.Column("roadmap_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("roadmap_week", sa.Integer(), nullable=True),
        sa.Column("mastery_at_decision", sa.Float(), nullable=True),
        sa.Column("current_difficulty", sa.Float(), nullable=True),
        sa.Column("target_difficulty", sa.Float(), nullable=True),
        sa.Column("recent_accuracy", sa.Float(), nullable=True),
        sa.Column("recent_avg_score", sa.Float(), nullable=True),
        sa.Column("recent_attempts", sa.Integer(), nullable=True),
        sa.Column("recent_response_time_seconds", sa.Float(), nullable=True),
        sa.Column("recent_window_size", sa.Integer(), nullable=True),
        sa.Column("candidate_question_count", sa.Integer(), nullable=False),
        sa.Column("selected_question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("selected_question_difficulty", sa.Float(), nullable=True),
        sa.Column("selection_reason", sa.String(length=100), nullable=False),
        sa.Column("baseline_average_score", sa.Float(), nullable=True),
        sa.Column("ability_difficulty", sa.Float(), nullable=True),
        sa.Column("skill_priority_rank", sa.Integer(), nullable=True),
        sa.Column("algorithm_version", sa.String(length=80), nullable=False),
        sa.Column("selection_policy_version", sa.String(length=80), nullable=False),
        sa.Column("experiment_group", sa.String(length=20), nullable=False, server_default="NONE"),
        sa.Column("data_origin", sa.String(length=20), nullable=False, server_default="UNKNOWN"),
        sa.Column("question_serve_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["roadmap_id"], ["member_roadmaps.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["selected_question_id"], ["questions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["question_serve_session_id"],
            ["question_serve_sessions.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_adaptive_decision_history_user_created",
        "adaptive_decision_history",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_adaptive_decision_history_question",
        "adaptive_decision_history",
        ["selected_question_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_adaptive_decision_history_question", table_name="adaptive_decision_history")
    op.drop_index("ix_adaptive_decision_history_user_created", table_name="adaptive_decision_history")
    op.drop_table("adaptive_decision_history")

    for name in (
        "response_time_status",
        "recent_window_size",
        "recent_response_time_seconds",
        "recent_attempts",
        "recent_avg_score",
        "recent_accuracy",
    ):
        op.drop_column("question_attempt_history", name)

    op.drop_constraint("fk_questions_verified_by_id", "questions", type_="foreignkey")
    op.drop_constraint("fk_questions_parent_question_id", "questions", type_="foreignkey")
    for name in (
        "verified_at",
        "verified_by_id",
        "verified_status",
        "parent_question_id",
        "is_adapted",
        "is_original",
        "source_license",
        "source_url",
        "source_name",
    ):
        op.drop_column("questions", name)

    op.drop_constraint(
        "uq_research_participation_participant_code",
        "research_participation",
        type_="unique",
    )
    op.drop_column("research_participation", "participant_code")
    op.execute("DROP SEQUENCE research_participant_code_seq")
