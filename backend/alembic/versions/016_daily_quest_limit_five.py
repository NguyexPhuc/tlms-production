"""daily quest limit five

Revision ID: 016_daily_quest_limit_five
Revises: 015_daily_quests
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "016_daily_quest_limit_five"
down_revision: Union[str, None] = "015_daily_quests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE quest_limit_configs ALTER COLUMN quest_limit SET DEFAULT 5")
    op.execute(
        """
        UPDATE quest_limit_configs
        SET quest_limit = 5, updated_at = now()
        WHERE role IN ('candidate', 'member')
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE quest_limit_configs ALTER COLUMN quest_limit SET DEFAULT 3")
    op.execute(
        """
        UPDATE quest_limit_configs
        SET quest_limit = 3, updated_at = now()
        WHERE role IN ('candidate', 'member')
        """
    )
