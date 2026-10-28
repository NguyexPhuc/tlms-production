"""member 8 week roadmaps

Revision ID: 019_member_roadmaps
Revises: 018_quest_proof_limit_ai_review
Create Date: 2026-09-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "019_member_roadmaps"
down_revision: Union[str, None] = "018_quest_proof_limit_ai_review"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "member_roadmaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("target_end_at", sa.DateTime(), nullable=False),
        sa.Column("current_week", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_day", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("total_weeks", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("total_days", sa.Integer(), nullable=False, server_default="56"),
        sa.Column("progress_percentage", sa.Float(), nullable=False, server_default="12.5"),
        sa.Column("current_stage", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_member_roadmaps_user_id"),
    )
    op.create_index("ix_member_roadmaps_user_id", "member_roadmaps", ["user_id"])
    op.create_index("ix_member_roadmaps_status", "member_roadmaps", ["status"])

    op.create_table(
        "member_roadmap_weeks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("roadmap_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("stage", sa.String(length=120), nullable=False),
        sa.Column("goals", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("question_focus", sa.Text(), nullable=False),
        sa.Column("daily_task_focus", sa.Text(), nullable=False),
        sa.Column("quest_focus", sa.Text(), nullable=False),
        sa.Column("skill_targets", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("progress_percentage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("weekly_evaluation", sa.Text(), nullable=True),
        sa.Column("planned_start_at", sa.DateTime(), nullable=False),
        sa.Column("planned_end_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["roadmap_id"], ["member_roadmaps.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("roadmap_id", "week_number", name="uq_member_roadmap_weeks_roadmap_week"),
    )
    op.create_index("ix_member_roadmap_weeks_roadmap_id", "member_roadmap_weeks", ["roadmap_id"])
    op.create_index("ix_member_roadmap_weeks_week_number", "member_roadmap_weeks", ["week_number"])


def downgrade() -> None:
    op.drop_index("ix_member_roadmap_weeks_week_number", table_name="member_roadmap_weeks")
    op.drop_index("ix_member_roadmap_weeks_roadmap_id", table_name="member_roadmap_weeks")
    op.drop_table("member_roadmap_weeks")

    op.drop_index("ix_member_roadmaps_status", table_name="member_roadmaps")
    op.drop_index("ix_member_roadmaps_user_id", table_name="member_roadmaps")
    op.drop_table("member_roadmaps")
