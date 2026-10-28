from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models.certification import Certificate, CourseEnrollment, ExamResult
from app.schemas.certification import ExamCreate, ExamQuestionCreate
from app.schemas.question import QuestionCreate
from app.services import certification as certification_module
from app.services.certification import CertificationService, VerificationRateLimiter


def test_proficiency_level_boundaries():
    service = CertificationService()
    assert service.proficiency_level(95) == "Expert"
    assert service.proficiency_level(85) == "Advanced"
    assert service.proficiency_level(70) == "Proficient"
    assert service.proficiency_level(69.99) == "Developing"


def test_exam_schema_rejects_duplicate_positions():
    shared = {
        "course_id": "07e41b99-59f2-440c-8bb7-26c6948011c2",
        "title": "Secure backend exam",
        "questions": [
            ExamQuestionCreate(
                question_id="c57c4d0f-d3b1-460d-9b3c-f8d9ddf1c3c2",
                position=1,
            ),
            ExamQuestionCreate(
                question_id="3d1186da-dcc6-4b35-8932-dfcf83e19eac",
                position=1,
            ),
        ],
    }
    with pytest.raises(ValidationError):
        ExamCreate(**shared)


def test_database_constraints_prevent_duplicate_results_and_certificates():
    result_constraints = {constraint.name for constraint in ExamResult.__table__.constraints}
    certificate_constraints = {constraint.name for constraint in Certificate.__table__.constraints}
    assert any(column.unique for column in ExamResult.__table__.columns if column.name == "attempt_id")
    assert any(column.unique for column in Certificate.__table__.columns if column.name == "exam_result_id")
    assert "exam_results_pkey" in result_constraints or None in result_constraints
    assert "certificates_pkey" in certificate_constraints or None in certificate_constraints
    assert any(constraint.name == "uq_course_enrollment_user" for constraint in CourseEnrollment.__table__.constraints)


def test_multiple_choice_question_requires_valid_server_answers():
    question = QuestionCreate(
        title="Secure API",
        question="Which controls protect an API?",
        question_type="multiple_choice",
        options={"A": "Authentication", "B": "Authorization", "C": "No validation", "D": "Public secrets"},
        correct_options=["a", "B"],
    )
    assert question.correct_options == ["A", "B"]
    assert question.correct_option is None

    with pytest.raises(ValidationError):
        QuestionCreate(
            title="Invalid",
            question="Choose answers",
            question_type="multiple_choice",
            options={"A": "One", "B": "Two"},
            correct_options=["D"],
        )


def test_verification_rate_limiter_rejects_request_over_limit(monkeypatch):
    monkeypatch.setattr(certification_module.settings, "CERTIFICATE_VERIFY_RATE_LIMIT", 2)
    limiter = VerificationRateLimiter()
    assert limiter.allow("127.0.0.1") is True
    assert limiter.allow("127.0.0.1") is True
    assert limiter.allow("127.0.0.1") is False


def test_pdf_renderer_creates_a4_certificate_with_unicode_name(tmp_path, monkeypatch):
    monkeypatch.setattr(certification_module.settings, "CERTIFICATE_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(certification_module.settings, "PUBLIC_WEB_URL", "https://example.test")
    certificate = SimpleNamespace(
        id="ea628bd4-15c7-43b4-b68b-b41ee7c0cbcf",
        certificate_id="TECH-2026-A8F42D",
        full_name="Nguyễn Ngọc Quang Phúc",
        certificate_name="Digital Technology Foundation",
        issuer_name="T&A Lab",
        score=92.5,
        proficiency_level="Advanced",
        issued_at=datetime(2026, 10, 27),
        expires_at=None,
        verification_token="secure-verification-token",
    )
    template = SimpleNamespace(
        background_color="#FFFCF5",
        primary_color="#C8102E",
        secondary_color="#101D35",
        accent_color="#C6A15B",
        organization_name="T&A Lab",
        title="CERTIFICATE OF ACHIEVEMENT",
        subtitle="DIGITAL TECHNOLOGY & PROFESSIONAL SKILLS",
        signature_name=None,
        signature_title=None,
    )

    output = Path(CertificationService().render_pdf(certificate, template))
    assert output.is_file()
    assert output.read_bytes().startswith(b"%PDF")
    assert output.stat().st_size > 10_000
