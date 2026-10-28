"""quest proof, limit quests, and ai review fields

Revision ID: 018_quest_proof_limit_ai_review
Revises: 017_seed_learning_roadmap_tasks
Create Date: 2026-09-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "018_quest_proof_limit_ai_review"
down_revision: Union[str, None] = "017_seed_learning_roadmap_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    op.execute("ALTER TYPE dailyqueststatus ADD VALUE IF NOT EXISTS 'submitted'")
    op.execute("ALTER TYPE dailyqueststatus ADD VALUE IF NOT EXISTS 'ai_reviewed'")
    op.execute("ALTER TYPE dailyqueststatus ADD VALUE IF NOT EXISTS 'rejected'")

    dailyquesttype = postgresql.ENUM("daily", "limit", name="dailyquesttype")
    dailyquesttype.create(bind, checkfirst=True)

    op.add_column(
        "daily_quests",
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "daily_quests",
        sa.Column(
            "quest_type",
            postgresql.ENUM("daily", "limit", name="dailyquesttype", create_type=False),
            nullable=False,
            server_default="daily",
        ),
    )
    op.add_column("daily_quests", sa.Column("proof_text", sa.Text(), nullable=True))
    op.add_column("daily_quests", sa.Column("proof_link", sa.String(length=500), nullable=True))
    op.add_column("daily_quests", sa.Column("proof_image_url", sa.String(length=500), nullable=True))
    op.add_column("daily_quests", sa.Column("proof_image_name", sa.String(length=255), nullable=True))
    op.add_column("daily_quests", sa.Column("submitted_at", sa.DateTime(), nullable=True))
    op.add_column("daily_quests", sa.Column("ai_score", sa.Float(), nullable=True))
    op.add_column("daily_quests", sa.Column("ai_feedback", sa.Text(), nullable=True))
    op.add_column("daily_quests", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column(
        "daily_quests",
        sa.Column("requires_image_proof", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "daily_quests",
        sa.Column("auto_pass_score", sa.Integer(), nullable=False, server_default="70"),
    )

    op.create_foreign_key(
        "fk_daily_quests_created_by_id_users",
        "daily_quests",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_daily_quests_created_by_id", "daily_quests", ["created_by_id"])
    op.create_index("ix_daily_quests_quest_type", "daily_quests", ["quest_type"])
    op.create_check_constraint(
        "ck_daily_quests_ai_score_range",
        "daily_quests",
        "ai_score IS NULL OR (ai_score >= 0 AND ai_score <= 100)",
    )
    op.create_check_constraint(
        "ck_daily_quests_auto_pass_score_range",
        "daily_quests",
        "auto_pass_score >= 0 AND auto_pass_score <= 100",
    )


def downgrade() -> None:
    op.drop_constraint("ck_daily_quests_auto_pass_score_range", "daily_quests", type_="check")
    op.drop_constraint("ck_daily_quests_ai_score_range", "daily_quests", type_="check")
    op.drop_index("ix_daily_quests_quest_type", table_name="daily_quests")
    op.drop_index("ix_daily_quests_created_by_id", table_name="daily_quests")
    op.drop_constraint("fk_daily_quests_created_by_id_users", "daily_quests", type_="foreignkey")

    op.drop_column("daily_quests", "auto_pass_score")
    op.drop_column("daily_quests", "requires_image_proof")
    op.drop_column("daily_quests", "reviewed_at")
    op.drop_column("daily_quests", "ai_feedback")
    op.drop_column("daily_quests", "ai_score")
    op.drop_column("daily_quests", "submitted_at")
    op.drop_column("daily_quests", "proof_image_name")
    op.drop_column("daily_quests", "proof_image_url")
    op.drop_column("daily_quests", "proof_link")
    op.drop_column("daily_quests", "proof_text")
    op.drop_column("daily_quests", "quest_type")
    op.drop_column("daily_quests", "created_by_id")

    op.execute("DROP TYPE IF EXISTS dailyquesttype")
