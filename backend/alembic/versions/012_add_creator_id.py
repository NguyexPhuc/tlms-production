"""add creator_id to tasks

Revision ID: 012_add_creator_id
Revises: 011_update_shifts
Create Date: 2026-03-26 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '012_add_creator_id'
down_revision = '011_update_shifts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add creator_id column to tasks table
    op.add_column('tasks', sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_tasks_creator_id_users',
        'tasks',
        'users',
        ['creator_id'],
        ['id']
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('fk_tasks_creator_id_users', 'tasks', type_='foreignkey')
    
    # Drop creator_id column
    op.drop_column('tasks', 'creator_id')
