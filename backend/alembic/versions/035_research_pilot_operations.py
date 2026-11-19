"""add fixed pilot sequence and research assessments

Revision ID: 035_research_pilot_operations
Revises: 034_adaptive_pilot_readiness
Create Date: 2026-11-17 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "035_research_pilot_operations"
down_revision: Union[str, None] = "034_adaptive_pilot_readiness"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "exams",
        sa.Column(
            "assessment_purpose",
            sa.String(length=30),
            nullable=False,
            server_default="CERTIFICATION",
        ),
    )
    op.create_check_constraint(
        "ck_exams_assessment_purpose",
        "exams",
        "assessment_purpose IN ('CERTIFICATION', 'RESEARCH_PRE', 'RESEARCH_POST')",
    )

    op.create_table(
        "research_studies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("study_code", sa.String(length=80), nullable=False),
        sa.Column("study_status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("fixed_sequence_version", sa.String(length=80), nullable=True),
        sa.Column("pre_exam_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("post_exam_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("git_commit", sa.String(length=64), nullable=True),
        sa.Column("adaptive_algorithm_version", sa.String(length=80), nullable=False, server_default="adaptive-v1"),
        sa.Column("adaptive_selection_policy_version", sa.String(length=80), nullable=False, server_default="question-selection-v1"),
        sa.Column("fixed_selection_policy_version", sa.String(length=80), nullable=False, server_default="fixed-sequence-v1"),
        sa.Column("question_bank_version", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["pre_exam_id"], ["exams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["post_exam_id"], ["exams.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("study_code", name="uq_research_studies_study_code"),
        sa.CheckConstraint(
            "study_status IN ('DRAFT', 'PILOT', 'ACTIVE', 'CLOSED')",
            name="ck_research_studies_status",
        ),
    )
    op.create_index("ix_research_studies_study_code", "research_studies", ["study_code"], unique=True)

    op.create_table(
        "research_fixed_question_sequences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("study_code", sa.String(length=80), nullable=False),
        sa.Column("sequence_version", sa.String(length=80), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["study_code"], ["research_studies.study_code"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "study_code", "sequence_version", "position",
            name="uq_research_fixed_sequence_position",
        ),
        sa.UniqueConstraint(
            "study_code", "sequence_version", "question_id",
            name="uq_research_fixed_sequence_question",
        ),
        sa.CheckConstraint("position > 0", name="ck_research_fixed_sequence_position_positive"),
    )
    op.create_index(
        "ix_research_fixed_sequence_active",
        "research_fixed_question_sequences",
        ["study_code", "sequence_version", "active", "position"],
    )

    op.add_column("adaptive_decision_history", sa.Column("sequence_position", sa.Integer(), nullable=True))
    op.add_column("adaptive_decision_history", sa.Column("sequence_version", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("adaptive_decision_history", "sequence_version")
    op.drop_column("adaptive_decision_history", "sequence_position")
    op.drop_index("ix_research_fixed_sequence_active", table_name="research_fixed_question_sequences")
    op.drop_table("research_fixed_question_sequences")
    op.drop_index("ix_research_studies_study_code", table_name="research_studies")
    op.drop_table("research_studies")
    op.drop_constraint("ck_exams_assessment_purpose", "exams", type_="check")
    op.drop_column("exams", "assessment_purpose")
