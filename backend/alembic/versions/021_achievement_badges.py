"""achievement badges

Revision ID: 021_achievement_badges
Revises: 020_adaptive_questions
Create Date: 2026-09-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "021_achievement_badges"
down_revision: Union[str, None] = "020_adaptive_questions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "achievement_badges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("metric", sa.String(length=80), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("badge_icon", sa.String(length=20), nullable=False, server_default="XP"),
        sa.Column("badge_color", sa.String(length=20), nullable=False, server_default="#1E90FF"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("code", name="uq_achievement_badges_code"),
    )
    op.create_index("ix_achievement_badges_category", "achievement_badges", ["category"])
    op.create_index("ix_achievement_badges_metric", "achievement_badges", ["metric"])

    op.create_table(
        "user_achievement_badges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("badge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("progress_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unlocked_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["badge_id"], ["achievement_badges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "badge_id", name="uq_user_achievement_badges_user_badge"),
    )
    op.create_index("ix_user_achievement_badges_user_id", "user_achievement_badges", ["user_id"])
    op.create_index("ix_user_achievement_badges_badge_id", "user_achievement_badges", ["badge_id"])


def downgrade() -> None:
    op.drop_index("ix_user_achievement_badges_badge_id", table_name="user_achievement_badges")
    op.drop_index("ix_user_achievement_badges_user_id", table_name="user_achievement_badges")
    op.drop_table("user_achievement_badges")

    op.drop_index("ix_achievement_badges_metric", table_name="achievement_badges")
    op.drop_index("ix_achievement_badges_category", table_name="achievement_badges")
    op.drop_table("achievement_badges")
