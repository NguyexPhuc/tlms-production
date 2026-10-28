"""add task scope columns

Revision ID: 007_add_task_scope
Revises: 006_schedules_registered_at
Create Date: 2026-01-31 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007_add_task_scope'
down_revision: Union[str, None] = '006_schedules_registered_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create TaskScope Enum
    taskscope = postgresql.ENUM('mandatory', 'opt_in', 'private', name='taskscope')
    taskscope.create(op.get_bind(), checkfirst=True)

    # Add columns
    with op.batch_alter_table('tasks') as batch_op:
        batch_op.add_column(sa.Column('scope', postgresql.ENUM('mandatory', 'opt_in', 'private', name='taskscope', create_type=False), nullable=False, server_default='mandatory'))
        batch_op.add_column(sa.Column('max_participants', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('assignee_ids', postgresql.ARRAY(sa.String(36)), nullable=False, server_default='{}'))


def downgrade() -> None:
    with op.batch_alter_table('tasks') as batch_op:
        batch_op.drop_column('assignee_ids')
        batch_op.drop_column('max_participants')
        batch_op.drop_column('scope')
    
    taskscope = postgresql.ENUM('mandatory', 'opt_in', 'private', name='taskscope')
    taskscope.drop(op.get_bind(), checkfirst=True)
