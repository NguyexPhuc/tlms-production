"""Create tasks and user_tasks tables

Revision ID: 003
Revises: 002_roles_array
Create Date: 2026-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_tasks'
down_revision: Union[str, None] = '002_roles_array'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    tasktype = postgresql.ENUM('core', 'bounty', name='tasktype')
    tasktype.create(op.get_bind(), checkfirst=True)
    
    taskdifficulty = postgresql.ENUM('easy', 'medium', 'hard', 'expert', name='taskdifficulty')
    taskdifficulty.create(op.get_bind(), checkfirst=True)
    
    taskstatus = postgresql.ENUM(
        'locked', 'available', 'in_progress', 'submitted', 'approved', 'rejected', 'completed',
        name='taskstatus'
    )
    taskstatus.create(op.get_bind(), checkfirst=True)
    
    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('type', postgresql.ENUM('core', 'bounty', name='tasktype', create_type=False), nullable=False),
        sa.Column('difficulty', postgresql.ENUM('easy', 'medium', 'hard', 'expert', name='taskdifficulty', create_type=False), nullable=False, server_default='medium'),
        sa.Column('min_level_required', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('prerequisite_task_ids', postgresql.ARRAY(sa.String(36)), nullable=False, server_default='{}'),
        sa.Column('xp_reward', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skill_tags', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('reference_links', postgresql.ARRAY(sa.String(500)), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'))
    )
    
    # Create indexes for tasks
    op.create_index('ix_tasks_type', 'tasks', ['type'])
    op.create_index('ix_tasks_is_active', 'tasks', ['is_active'])
    
    # Create user_tasks table
    op.create_table(
        'user_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM('locked', 'available', 'in_progress', 'submitted', 'approved', 'rejected', 'completed', name='taskstatus', create_type=False), nullable=False, server_default='available'),
        sa.Column('proof_link', sa.String(500), nullable=True),
        sa.Column('submission_notes', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('mentor_comment', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('xp_earned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='SET NULL')
    )
    
    # Create indexes for user_tasks
    op.create_index('ix_user_tasks_user_id', 'user_tasks', ['user_id'])
    op.create_index('ix_user_tasks_task_id', 'user_tasks', ['task_id'])
    op.create_index('ix_user_tasks_status', 'user_tasks', ['status'])
    op.create_index('ix_user_tasks_user_task', 'user_tasks', ['user_id', 'task_id'], unique=True)


def downgrade() -> None:
    # Drop tables
    op.drop_index('ix_user_tasks_user_task', table_name='user_tasks')
    op.drop_index('ix_user_tasks_status', table_name='user_tasks')
    op.drop_index('ix_user_tasks_task_id', table_name='user_tasks')
    op.drop_index('ix_user_tasks_user_id', table_name='user_tasks')
    op.drop_table('user_tasks')
    
    op.drop_index('ix_tasks_is_active', table_name='tasks')
    op.drop_index('ix_tasks_type', table_name='tasks')
    op.drop_table('tasks')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS taskstatus")
    op.execute("DROP TYPE IF EXISTS taskdifficulty")
    op.execute("DROP TYPE IF EXISTS tasktype")
