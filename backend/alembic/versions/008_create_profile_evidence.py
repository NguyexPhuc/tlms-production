"""create profile evidence table

Revision ID: 008_create_profile_evidence
Revises: 007_add_task_scope
Create Date: 2026-01-31 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008_create_profile_evidence'
down_revision: Union[str, None] = '007_add_task_scope'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create EvidenceStatus Enum
    evidencestatus = postgresql.ENUM('pending', 'verified', 'rejected', name='evidencestatus')
    evidencestatus.create(op.get_bind(), checkfirst=True)
    
    # Create profile_evidence table
    op.create_table(
        'profile_evidence',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=True),
        
        # Evidence details
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('evidence_links', postgresql.ARRAY(sa.String(500)), nullable=False, server_default='{}'),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),
        
        # Verification
        sa.Column('status', postgresql.ENUM('pending', 'verified', 'rejected', name='evidencestatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('verified_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('verification_notes', sa.Text(), nullable=True),
        
        # Display settings
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes
    op.create_index('ix_profile_evidence_user_id', 'profile_evidence', ['user_id'])
    op.create_index('ix_profile_evidence_task_id', 'profile_evidence', ['task_id'])
    op.create_index('ix_profile_evidence_status', 'profile_evidence', ['status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_profile_evidence_status')
    op.drop_index('ix_profile_evidence_task_id')
    op.drop_index('ix_profile_evidence_user_id')
    
    # Drop table
    op.drop_table('profile_evidence')
    
    # Drop enum
    evidencestatus = postgresql.ENUM('pending', 'verified', 'rejected', name='evidencestatus')
    evidencestatus.drop(op.get_bind(), checkfirst=True)
