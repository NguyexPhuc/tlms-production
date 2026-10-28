"""add registered_at to schedules

Revision ID: 006_schedules_registered_at
Revises: 005_add_student_schedule
Create Date: 2026-01-30 09:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = '006_schedules_registered_at'
down_revision = '005_add_student_schedule'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    bind = op.get_context().bind
    inspector = Inspector.from_engine(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not column_exists('schedules', 'registered_at'):
        op.add_column('schedules', sa.Column('registered_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))


def downgrade() -> None:
    if column_exists('schedules', 'registered_at'):
        op.drop_column('schedules', 'registered_at')
