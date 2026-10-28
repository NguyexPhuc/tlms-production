"""create schedules and attendances tables

Revision ID: 004
Revises: 003
Create Date: 2024-01-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_schedules'
down_revision = '003_tasks'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create schedules table
    op.create_table(
        'schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('work_date', sa.Date(), nullable=False),
        sa.Column('shift', sa.String(20), nullable=False),  # morning, afternoon, evening
        sa.Column('is_cancelled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    
    # Create indexes for schedules
    op.create_index('ix_schedules_user_id', 'schedules', ['user_id'])
    op.create_index('ix_schedules_work_date', 'schedules', ['work_date'])
    op.create_index('ix_schedules_user_date_shift', 'schedules', ['user_id', 'work_date', 'shift'], unique=True)
    
    # Create attendances table
    op.create_table(
        'attendances',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('schedule_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('schedules.id', ondelete='SET NULL'), nullable=True),
        sa.Column('work_date', sa.Date(), nullable=False),
        sa.Column('shift', sa.String(20), nullable=False),
        sa.Column('check_in_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('check_out_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),  # pending, present, absent, late, early_leave, extra
        sa.Column('discipline_points_change', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('bonus_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('auto_reconciled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('reconciled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    
    # Create indexes for attendances
    op.create_index('ix_attendances_user_id', 'attendances', ['user_id'])
    op.create_index('ix_attendances_work_date', 'attendances', ['work_date'])
    op.create_index('ix_attendances_schedule_id', 'attendances', ['schedule_id'])
    op.create_index('ix_attendances_status', 'attendances', ['status'])


def downgrade() -> None:
    op.drop_index('ix_attendances_status', 'attendances')
    op.drop_index('ix_attendances_schedule_id', 'attendances')
    op.drop_index('ix_attendances_work_date', 'attendances')
    op.drop_index('ix_attendances_user_id', 'attendances')
    op.drop_table('attendances')
    
    op.drop_index('ix_schedules_user_date_shift', 'schedules')
    op.drop_index('ix_schedules_work_date', 'schedules')
    op.drop_index('ix_schedules_user_id', 'schedules')
    op.drop_table('schedules')
