"""add phone column to users table

Revision ID: 009_add_phone_column
Revises: 008_create_profile_evidence
Create Date: 2026-03-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009_add_phone_column'
down_revision: Union[str, None] = '008_create_profile_evidence'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add phone column to users table
    op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))
    
    # Create index on phone for faster lookups
    op.create_index('ix_users_phone', 'users', ['phone'], unique=False)


def downgrade() -> None:
    # Drop index first
    op.drop_index('ix_users_phone', table_name='users')
    
    # Remove phone column
    op.drop_column('users', 'phone')
