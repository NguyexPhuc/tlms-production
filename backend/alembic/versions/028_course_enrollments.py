"""course enrollments

Revision ID: 028_course_enrollments
Revises: 027_digital_certification
Create Date: 2026-10-27 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "028_course_enrollments"
down_revision: Union[str, None] = "027_digital_certification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("progress_percentage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("enrolled_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("course_id", "user_id", name="uq_course_enrollment_user"),
        sa.CheckConstraint("progress_percentage >= 0 AND progress_percentage <= 100", name="ck_course_enrollment_progress"),
    )
    op.create_index("ix_course_enrollments_user", "course_enrollments", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_course_enrollments_user", table_name="course_enrollments")
    op.drop_table("course_enrollments")
