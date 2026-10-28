"""digital certification platform

Revision ID: 027_digital_certification
Revises: 026_question_concepts
Create Date: 2026-10-27 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "027_digital_certification"
down_revision: Union[str, None] = "026_question_concepts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)

    op.create_table(
        "certificate_templates",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("organization_name", sa.String(255), nullable=False, server_default="T&A Lab"),
        sa.Column("title", sa.String(255), nullable=False, server_default="CERTIFICATE OF ACHIEVEMENT"),
        sa.Column("subtitle", sa.String(255), nullable=False, server_default="DIGITAL TECHNOLOGY & PROFESSIONAL SKILLS"),
        sa.Column("primary_color", sa.String(20), nullable=False, server_default="#C8102E"),
        sa.Column("secondary_color", sa.String(20), nullable=False, server_default="#101D35"),
        sa.Column("accent_color", sa.String(20), nullable=False, server_default="#C6A15B"),
        sa.Column("background_color", sa.String(20), nullable=False, server_default="#FFFCF5"),
        sa.Column("logo_storage_key", sa.String(500), nullable=True),
        sa.Column("background_storage_key", sa.String(500), nullable=True),
        sa.Column("signature_name", sa.String(160), nullable=True),
        sa.Column("signature_title", sa.String(160), nullable=True),
        sa.Column("font_family", sa.String(100), nullable=False, server_default="DejaVu Sans"),
        sa.Column("layout", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_id", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "courses",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("certificate_template_id", uuid, sa.ForeignKey("certificate_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_id", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("code", name="uq_courses_code"),
    )
    op.create_index("ix_courses_code", "courses", ["code"])

    op.create_table(
        "lessons",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("course_id", uuid, sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("course_id", "position", name="uq_lessons_course_position"),
    )

    op.create_table(
        "exams",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("course_id", uuid, sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("pass_percentage", sa.Float(), nullable=False, server_default="80"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("certificate_name", sa.String(255), nullable=True),
        sa.Column("certificate_valid_days", sa.Integer(), nullable=True),
        sa.Column("opens_at", sa.DateTime(), nullable=True),
        sa.Column("closes_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("duration_minutes > 0", name="ck_exams_duration_positive"),
        sa.CheckConstraint("pass_percentage >= 0 AND pass_percentage <= 100", name="ck_exams_pass_percentage"),
        sa.CheckConstraint("max_attempts > 0", name="ck_exams_max_attempts_positive"),
    )

    op.create_table(
        "exam_questions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("exam_id", uuid, sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", uuid, sa.ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("points", sa.Float(), nullable=False, server_default="1"),
        sa.Column("correct_options", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("exam_id", "question_id", name="uq_exam_questions_exam_question"),
        sa.UniqueConstraint("exam_id", "position", name="uq_exam_questions_exam_position"),
        sa.CheckConstraint("points > 0", name="ck_exam_questions_points_positive"),
    )

    op.create_table(
        "exam_attempts",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("exam_id", uuid, sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="in_progress"),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("exam_id", "user_id", "attempt_number", name="uq_exam_attempt_number"),
    )
    op.create_index("ix_exam_attempts_status", "exam_attempts", ["status"])
    op.create_index("ix_exam_attempts_exam_user", "exam_attempts", ["exam_id", "user_id"])

    op.create_table(
        "exam_answers",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("attempt_id", uuid, sa.ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_question_id", uuid, sa.ForeignKey("exam_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("selected_options", sa.JSON(), nullable=True),
        sa.Column("text_answer", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("score_awarded", sa.Float(), nullable=True),
        sa.Column("reviewer_feedback", sa.Text(), nullable=True),
        sa.Column("reviewed_by_id", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("attempt_id", "exam_question_id", name="uq_exam_answer_question"),
    )

    op.create_table(
        "exam_results",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("attempt_id", uuid, sa.ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_id", uuid, sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("max_score", sa.Float(), nullable=False),
        sa.Column("percentage", sa.Float(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("proficiency_level", sa.String(50), nullable=False),
        sa.Column("graded_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_exam_results_user_exam", "exam_results", ["user_id", "exam_id"])

    op.create_table(
        "certificates",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("certificate_id", sa.String(50), nullable=False, unique=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_id", uuid, sa.ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("exam_result_id", uuid, sa.ForeignKey("exam_results.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("template_id", uuid, sa.ForeignKey("certificate_templates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("certificate_name", sa.String(255), nullable=False),
        sa.Column("issuer_name", sa.String(255), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("proficiency_level", sa.String(50), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("issued_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="valid"),
        sa.Column("verification_token", sa.String(100), nullable=False, unique=True),
        sa.Column("pdf_storage_key", sa.String(500), nullable=True),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("score_is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_certificates_certificate_id", "certificates", ["certificate_id"])
    op.create_index("ix_certificates_verification_token", "certificates", ["verification_token"])
    op.create_index("ix_certificates_status", "certificates", ["status"])
    op.create_index("ix_certificates_user", "certificates", ["user_id"])

    op.create_table(
        "certificate_audit_logs",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("certificate_id", uuid, sa.ForeignKey("certificates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_certificate_audit_certificate", "certificate_audit_logs", ["certificate_id", "created_at"])

    op.create_table(
        "certificate_verification_logs",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("certificate_id", uuid, sa.ForeignKey("certificates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("token_fingerprint", sa.String(64), nullable=False),
        sa.Column("result", sa.String(30), nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_certificate_verification_fingerprint", "certificate_verification_logs", ["token_fingerprint"])


def downgrade() -> None:
    op.drop_table("certificate_verification_logs")
    op.drop_table("certificate_audit_logs")
    op.drop_table("certificates")
    op.drop_table("exam_results")
    op.drop_table("exam_answers")
    op.drop_table("exam_attempts")
    op.drop_table("exam_questions")
    op.drop_table("exams")
    op.drop_table("lessons")
    op.drop_table("courses")
    op.drop_table("certificate_templates")
