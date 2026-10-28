"""weekly cups

Revision ID: 022_weekly_cups
Revises: 021_achievement_badges
Create Date: 2026-10-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "022_weekly_cups"
down_revision: Union[str, None] = "021_achievement_badges"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cup_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon", sa.String(length=20), nullable=False, server_default="CUP"),
        sa.Column("color", sa.String(length=20), nullable=False, server_default="#f59e0b"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("code", name="uq_cup_definitions_code"),
    )
    op.create_index("ix_cup_definitions_sort_order", "cup_definitions", ["sort_order"])

    op.create_table(
        "weekly_cup_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cup_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("opens_at", sa.DateTime(), nullable=False),
        sa.Column("closes_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="open"),
        sa.Column("winner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("winner_score", sa.Float(), nullable=True),
        sa.Column("awarded_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["cup_id"], ["cup_definitions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["winner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("cup_id", name="uq_weekly_cup_events_cup_id"),
        sa.UniqueConstraint("week_start", name="uq_weekly_cup_events_week_start"),
    )
    op.create_index("ix_weekly_cup_events_status", "weekly_cup_events", ["status"])
    op.create_index("ix_weekly_cup_events_week_start", "weekly_cup_events", ["week_start"])
    op.create_index("ix_weekly_cup_events_winner_user_id", "weekly_cup_events", ["winner_user_id"])

    op.create_table(
        "user_cups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cup_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("score_snapshot", sa.Float(), nullable=False, server_default="0"),
        sa.Column("discipline_score_snapshot", sa.Float(), nullable=False, server_default="0"),
        sa.Column("awarded_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["cup_id"], ["cup_definitions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["event_id"], ["weekly_cup_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("cup_id", name="uq_user_cups_cup_id"),
        sa.UniqueConstraint("event_id", name="uq_user_cups_event_id"),
    )
    op.create_index("ix_user_cups_user_id", "user_cups", ["user_id"])
    op.create_index("ix_user_cups_cup_id", "user_cups", ["cup_id"])


def downgrade() -> None:
    op.drop_index("ix_user_cups_cup_id", table_name="user_cups")
    op.drop_index("ix_user_cups_user_id", table_name="user_cups")
    op.drop_table("user_cups")

    op.drop_index("ix_weekly_cup_events_winner_user_id", table_name="weekly_cup_events")
    op.drop_index("ix_weekly_cup_events_week_start", table_name="weekly_cup_events")
    op.drop_index("ix_weekly_cup_events_status", table_name="weekly_cup_events")
    op.drop_table("weekly_cup_events")

    op.drop_index("ix_cup_definitions_sort_order", table_name="cup_definitions")
    op.drop_table("cup_definitions")
