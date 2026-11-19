"""add participant research survey responses

Revision ID: 037_research_participant_survey
Revises: 036_real_pilot_question_bank
Create Date: 2026-11-19 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "037_research_participant_survey"
down_revision: Union[str, None] = "036_real_pilot_question_bank"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_survey_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("participation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("study_code", sa.String(length=80), nullable=False),
        sa.Column("likert_answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("useful_feedback", sa.Text(), nullable=True),
        sa.Column("improvement_feedback", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["participation_id"],
            ["research_participation.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["study_code"],
            ["research_studies.study_code"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "participation_id",
            name="uq_research_survey_responses_participation",
        ),
    )
    op.create_index(
        "ix_research_survey_responses_study",
        "research_survey_responses",
        ["study_code", "submitted_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_research_survey_responses_study",
        table_name="research_survey_responses",
    )
    op.drop_table("research_survey_responses")
