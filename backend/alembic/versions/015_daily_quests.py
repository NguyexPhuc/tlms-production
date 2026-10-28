"""daily quests

Revision ID: 015_daily_quests
Revises: 014_member_development
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "015_daily_quests"
down_revision: Union[str, None] = "014_member_development"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    dailyquestdifficulty = postgresql.ENUM("easy", "medium", "hard", name="dailyquestdifficulty")
    dailyquestdifficulty.create(bind, checkfirst=True)

    dailyqueststatus = postgresql.ENUM(
        "pending",
        "in_progress",
        "completed",
        "expired",
        name="dailyqueststatus",
    )
    dailyqueststatus.create(bind, checkfirst=True)

    op.create_table(
        "daily_quests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "difficulty",
            postgresql.ENUM("easy", "medium", "hard", name="dailyquestdifficulty", create_type=False),
            nullable=False,
            server_default="easy",
        ),
        sa.Column("xp_reward", sa.Integer(), nullable=False, server_default="10"),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "in_progress",
                "completed",
                "expired",
                name="dailyqueststatus",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("xp_reward >= 0", name="ck_daily_quests_xp_reward_non_negative"),
    )
    op.create_index("ix_daily_quests_user_id", "daily_quests", ["user_id"])
    op.create_index("ix_daily_quests_status", "daily_quests", ["status"])
    op.create_index("ix_daily_quests_expires_at", "daily_quests", ["expires_at"])
    op.create_index("ix_daily_quests_user_created_at", "daily_quests", ["user_id", "created_at"])
    op.create_index("ix_daily_quests_user_status_expires_at", "daily_quests", ["user_id", "status", "expires_at"])

    op.create_table(
        "quest_limit_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column("min_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_level", sa.Integer(), nullable=True),
        sa.Column("quest_limit", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("min_level >= 1", name="ck_quest_limit_configs_min_level_positive"),
        sa.CheckConstraint("quest_limit >= 1", name="ck_quest_limit_configs_quest_limit_positive"),
        sa.CheckConstraint("max_level IS NULL OR max_level >= min_level", name="ck_quest_limit_configs_level_range"),
    )
    op.create_index("ix_quest_limit_configs_role", "quest_limit_configs", ["role"])
    op.create_index("ix_quest_limit_configs_level_range", "quest_limit_configs", ["min_level", "max_level"])

    limit_table = sa.table(
        "quest_limit_configs",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("role", sa.String),
        sa.column("min_level", sa.Integer),
        sa.column("max_level", sa.Integer),
        sa.column("quest_limit", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        limit_table,
        [
            {
                "id": uuid.uuid4(),
                "role": "candidate",
                "min_level": 1,
                "max_level": None,
                "quest_limit": 5,
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "role": "member",
                "min_level": 1,
                "max_level": None,
                "quest_limit": 5,
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_quest_limit_configs_level_range", table_name="quest_limit_configs")
    op.drop_index("ix_quest_limit_configs_role", table_name="quest_limit_configs")
    op.drop_table("quest_limit_configs")

    op.drop_index("ix_daily_quests_user_status_expires_at", table_name="daily_quests")
    op.drop_index("ix_daily_quests_user_created_at", table_name="daily_quests")
    op.drop_index("ix_daily_quests_expires_at", table_name="daily_quests")
    op.drop_index("ix_daily_quests_status", table_name="daily_quests")
    op.drop_index("ix_daily_quests_user_id", table_name="daily_quests")
    op.drop_table("daily_quests")

    op.execute("DROP TYPE IF EXISTS dailyqueststatus")
    op.execute("DROP TYPE IF EXISTS dailyquestdifficulty")
