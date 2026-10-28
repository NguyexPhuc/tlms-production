"""Change role to roles array

Revision ID: 002
Revises: 001
Create Date: 2026-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_roles_array'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new roles column as array
    op.add_column('users', sa.Column('roles', postgresql.ARRAY(sa.String(50)), nullable=True))
    
    # Migrate data: convert single role to array
    op.execute("""
        UPDATE users 
        SET roles = ARRAY[role::text]
        WHERE role IS NOT NULL
    """)
    
    # Set default for new column
    op.execute("""
        UPDATE users 
        SET roles = ARRAY['candidate']
        WHERE roles IS NULL
    """)
    
    # Make roles not nullable
    op.alter_column('users', 'roles', nullable=False)
    
    # Drop old role column and enum type
    op.drop_column('users', 'role')
    op.execute("DROP TYPE IF EXISTS userrole")


def downgrade() -> None:
    # Recreate enum type
    userrole = postgresql.ENUM('candidate', 'member', 'mentor', 'admin', name='userrole')
    userrole.create(op.get_bind())
    
    # Add role column back
    op.add_column('users', sa.Column('role', userrole, nullable=True))
    
    # Migrate: take first (or highest priority) role from array
    op.execute("""
        UPDATE users 
        SET role = CASE 
            WHEN 'admin' = ANY(roles) THEN 'admin'::userrole
            WHEN 'mentor' = ANY(roles) THEN 'mentor'::userrole
            WHEN 'member' = ANY(roles) THEN 'member'::userrole
            ELSE 'candidate'::userrole
        END
    """)
    
    # Make role not nullable
    op.alter_column('users', 'role', nullable=False)
    
    # Drop roles array column
    op.drop_column('users', 'roles')
