"""add real pilot study metadata and question-bank mapping

Revision ID: 036_real_pilot_question_bank
Revises: 035_research_pilot_operations
Create Date: 2026-11-17 19:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "036_real_pilot_question_bank"
down_revision: Union[str, None] = "035_research_pilot_operations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("research_studies", sa.Column("name", sa.String(length=255), nullable=True))
    op.add_column("research_studies", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "research_participation",
        sa.Column("consent_granted_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "research_study_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("study_code", sa.String(length=80), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phase", sa.String(length=10), nullable=False),
        sa.Column("external_question_id", sa.String(length=120), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["study_code"], ["research_studies.study_code"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("study_code", "question_id", name="uq_research_study_questions_question"),
        sa.UniqueConstraint(
            "study_code", "phase", "external_question_id",
            name="uq_research_study_questions_external",
        ),
        sa.CheckConstraint("phase IN ('PRE', 'TRAIN', 'POST')", name="ck_research_study_questions_phase"),
        sa.CheckConstraint("position > 0", name="ck_research_study_questions_position"),
    )
    op.create_index(
        "ix_research_study_questions_phase",
        "research_study_questions",
        ["study_code", "phase"],
    )


def downgrade() -> None:
    op.drop_index("ix_research_study_questions_phase", table_name="research_study_questions")
    op.drop_table("research_study_questions")
    op.drop_column("research_participation", "consent_granted_at")
    op.drop_column("research_studies", "description")
    op.drop_column("research_studies", "name")
