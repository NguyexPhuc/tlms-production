"""add student_id, class_schedules, and schedule fields

Revision ID: 005_add_student_schedule
Revises: 004_create_schedules_attendances_tables
Create Date: 2026-01-30 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '005_add_student_schedule'
down_revision = '004_schedules'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    bind = op.get_context().bind
    inspector = Inspector.from_engine(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns

def table_exists(table_name):
    bind = op.get_context().bind
    inspector = Inspector.from_engine(bind)
    return inspector.has_table(table_name)

def upgrade() -> None:
    # 1. Add student_id to users
    if not column_exists('users', 'student_id'):
        op.add_column('users', sa.Column('student_id', sa.String(), nullable=True))
        op.create_index(op.f('ix_users_student_id'), 'users', ['student_id'], unique=True)

    # 2. Add registration_type and cancellation fields to schedules
    # Create enum for registration type
    bind = op.get_context().bind
    try:
        registration_type = postgresql.ENUM('manual', 'auto', name='registrationtype')
        registration_type.create(bind, checkfirst=True)
    except Exception:
        pass # Enum likely exists

    if not column_exists('schedules', 'registration_type'):
        op.add_column('schedules', sa.Column('registration_type', sa.Enum('manual', 'auto', name='registrationtype'), server_default='manual', nullable=False))
    
    if not column_exists('schedules', 'is_cancelled'):
        op.add_column('schedules', sa.Column('is_cancelled', sa.Boolean(), server_default='false', nullable=False))
        
    if not column_exists('schedules', 'cancel_reason'):
        op.add_column('schedules', sa.Column('cancel_reason', sa.String(), nullable=True))

    # 3. Create class_schedules table
    if not table_exists('class_schedules'):
        op.create_table(
            'class_schedules',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('subject_name', sa.String(), nullable=False),
            sa.Column('room', sa.String(), nullable=True),
            sa.Column('start_datetime', sa.DateTime(), nullable=False),
            sa.Column('end_datetime', sa.DateTime(), nullable=False),
            sa.Column('is_cancelled', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('description', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_class_schedules_user_id'), 'class_schedules', ['user_id'], unique=False)
        op.create_index(op.f('ix_class_schedules_start_datetime'), 'class_schedules', ['start_datetime'], unique=False)


def downgrade() -> None:
    # Drop class_schedules
    if table_exists('class_schedules'):
        op.drop_index(op.f('ix_class_schedules_start_datetime'), table_name='class_schedules')
        op.drop_index(op.f('ix_class_schedules_user_id'), table_name='class_schedules')
        op.drop_table('class_schedules')

    # Drop fields from schedules
    if column_exists('schedules', 'cancel_reason'):
        op.drop_column('schedules', 'cancel_reason')
    if column_exists('schedules', 'is_cancelled'):
        op.drop_column('schedules', 'is_cancelled')
    if column_exists('schedules', 'registration_type'):
        op.drop_column('schedules', 'registration_type')
    
    # Drop enum
    bind = op.get_context().bind
    try:
        registration_type = postgresql.ENUM('manual', 'auto', name='registrationtype')
        registration_type.drop(bind, checkfirst=True)
    except Exception:
        pass

    # Drop fields from users
    if column_exists('users', 'student_id'):
        op.drop_index(op.f('ix_users_student_id'), table_name='users')
        op.drop_column('users', 'student_id')
