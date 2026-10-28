"""Course, exam and digital certificate persistence models."""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    skills = Column(JSON, default=list, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)
    certificate_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("certificate_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan")
    exams = relationship("Exam", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("CourseEnrollment", back_populates="course", cascade="all, delete-orphan")
    certificate_template = relationship("CertificateTemplate", foreign_keys=[certificate_template_id])


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("course_id", "position", name="uq_lessons_course_position"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    position = Column(Integer, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    course = relationship("Course", back_populates="lessons")


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (UniqueConstraint("course_id", "user_id", name="uq_course_enrollment_user"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(30), default="active", nullable=False)
    progress_percentage = Column(Float, default=0.0, nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    course = relationship("Course", back_populates="enrollments")
    user = relationship("User")


class Exam(Base):
    __tablename__ = "exams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, default=30, nullable=False)
    pass_percentage = Column(Float, default=80.0, nullable=False)
    max_attempts = Column(Integer, default=1, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)
    certificate_name = Column(String(255), nullable=True)
    certificate_valid_days = Column(Integer, nullable=True)
    opens_at = Column(DateTime, nullable=True)
    closes_at = Column(DateTime, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    course = relationship("Course", back_populates="exams")
    exam_questions = relationship(
        "ExamQuestion", back_populates="exam", cascade="all, delete-orphan", order_by="ExamQuestion.position"
    )
    attempts = relationship("ExamAttempt", back_populates="exam", cascade="all, delete-orphan")


class ExamQuestion(Base):
    __tablename__ = "exam_questions"
    __table_args__ = (
        UniqueConstraint("exam_id", "question_id", name="uq_exam_questions_exam_question"),
        UniqueConstraint("exam_id", "position", name="uq_exam_questions_exam_position"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False)
    position = Column(Integer, nullable=False)
    points = Column(Float, default=1.0, nullable=False)
    correct_options = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    exam = relationship("Exam", back_populates="exam_questions")
    question = relationship("Question")


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"
    __table_args__ = (UniqueConstraint("exam_id", "user_id", "attempt_number", name="uq_exam_attempt_number"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    status = Column(String(30), default="in_progress", nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    exam = relationship("Exam", back_populates="attempts")
    user = relationship("User")
    answers = relationship("ExamAnswer", back_populates="attempt", cascade="all, delete-orphan")
    result = relationship("ExamResult", back_populates="attempt", uselist=False, cascade="all, delete-orphan")


class ExamAnswer(Base):
    __tablename__ = "exam_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "exam_question_id", name="uq_exam_answer_question"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False)
    exam_question_id = Column(UUID(as_uuid=True), ForeignKey("exam_questions.id", ondelete="CASCADE"), nullable=False)
    selected_options = Column(JSON, nullable=True)
    text_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    score_awarded = Column(Float, nullable=True)
    reviewer_feedback = Column(Text, nullable=True)
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    attempt = relationship("ExamAttempt", back_populates="answers")
    exam_question = relationship("ExamQuestion")


class ExamResult(Base):
    __tablename__ = "exam_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey("exam_attempts.id", ondelete="CASCADE"), unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    percentage = Column(Float, nullable=False)
    passed = Column(Boolean, nullable=False)
    proficiency_level = Column(String(50), nullable=False)
    graded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    attempt = relationship("ExamAttempt", back_populates="result")
    certificate = relationship("Certificate", back_populates="exam_result", uselist=False)


class CertificateTemplate(Base):
    __tablename__ = "certificate_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(160), nullable=False)
    organization_name = Column(String(255), default="T&A Lab", nullable=False)
    title = Column(String(255), default="CERTIFICATE OF ACHIEVEMENT", nullable=False)
    subtitle = Column(String(255), default="DIGITAL TECHNOLOGY & PROFESSIONAL SKILLS", nullable=False)
    primary_color = Column(String(20), default="#C8102E", nullable=False)
    secondary_color = Column(String(20), default="#101D35", nullable=False)
    accent_color = Column(String(20), default="#C6A15B", nullable=False)
    background_color = Column(String(20), default="#FFFCF5", nullable=False)
    logo_storage_key = Column(String(500), nullable=True)
    background_storage_key = Column(String(500), nullable=True)
    signature_name = Column(String(160), nullable=True)
    signature_title = Column(String(160), nullable=True)
    font_family = Column(String(100), default="DejaVu Sans", nullable=False)
    layout = Column(JSON, default=dict, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certificate_id = Column(String(50), nullable=False, unique=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False)
    exam_result_id = Column(UUID(as_uuid=True), ForeignKey("exam_results.id", ondelete="RESTRICT"), unique=True, nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("certificate_templates.id", ondelete="RESTRICT"), nullable=False)
    full_name = Column(String(255), nullable=False)
    certificate_name = Column(String(255), nullable=False)
    issuer_name = Column(String(255), nullable=False)
    score = Column(Float, nullable=False)
    proficiency_level = Column(String(50), nullable=False)
    skills = Column(JSON, default=list, nullable=False)
    issued_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    status = Column(String(30), default="valid", nullable=False, index=True)
    verification_token = Column(String(100), nullable=False, unique=True, index=True)
    pdf_storage_key = Column(String(500), nullable=True)
    template_version = Column(Integer, nullable=False)
    score_is_public = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User")
    course = relationship("Course")
    exam_result = relationship("ExamResult", back_populates="certificate")
    template = relationship("CertificateTemplate")


class CertificateAuditLog(Base):
    __tablename__ = "certificate_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certificate_id = Column(UUID(as_uuid=True), ForeignKey("certificates.id", ondelete="CASCADE"), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)
    reason = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CertificateVerificationLog(Base):
    __tablename__ = "certificate_verification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certificate_id = Column(UUID(as_uuid=True), ForeignKey("certificates.id", ondelete="SET NULL"), nullable=True)
    token_fingerprint = Column(String(64), nullable=False, index=True)
    result = Column(String(30), nullable=False)
    ip_hash = Column(String(64), nullable=True)
    user_agent = Column(String(500), nullable=True)
    verified_at = Column(DateTime, default=datetime.utcnow, nullable=False)
