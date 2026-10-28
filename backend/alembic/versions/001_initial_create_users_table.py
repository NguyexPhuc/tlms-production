"""Create users table

Revision ID: 001
Revises: 
Create Date: 2026-01-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('s4h_user_id', sa.String(255), unique=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('role', sa.Enum('candidate', 'member', 'mentor', 'admin', name='userrole'), 
                  nullable=False, server_default='candidate'),
        sa.Column('status', sa.Enum('active', 'inactive', name='userstatus'), 
                  nullable=False, server_default='active'),
        sa.Column('current_xp', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('discipline_score', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('core_task_progress', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('is_ready_to_promote', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
    )
    
    # Create indexes
    op.create_index('ix_users_s4h_user_id', 'users', ['s4h_user_id'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'])


def downgrade() -> None:
    op.drop_index('ix_users_email')
    op.drop_index('ix_users_s4h_user_id')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS userrole')
    op.execute('DROP TYPE IF EXISTS userstatus')
