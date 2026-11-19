from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.routes import certifications
from app.models.certification import AssessmentPurpose
from app.models.development import (
    ResearchFixedQuestionSequence,
    ResearchParticipation,
    ResearchStudyQuestion,
    ResearchSurveyResponse,
)
from app.schemas.certification import ExamCreate, ExamQuestionCreate
from app.schemas.research import (
    FixedSequenceConfigure,
    ResearchEnrollmentRequest,
    ResearchSurveySubmit,
)
from app.scripts.export_research_dataset import PRE_POST_COLUMNS, build_export_rows
from app.services.certification import CertificationService
from app.services.question import QuestionService
from app.services.research import ResearchService, is_active_research_participant


def _question(position: int):
    return SimpleNamespace(
        id=uuid4(),
        title=f"Question {position}",
        skill_key="backend",
        topic="concurrency",
        numeric_difficulty=float(position),
    )


def test_fixed_sequence_preserves_position_and_ignores_adaptive_inputs():
    questions = [_question(3), _question(1), _question(2)]
    items = [
        SimpleNamespace(
            question_id=question.id,
            question=question,
            position=position,
            sequence_version="fixed-v1",
        )
        for position, question in zip([3, 1, 2], questions)
    ]

    selected, plan = QuestionService()._fixed_selection_plan(items, [])

    assert [question.title for question in selected] == ["Question 1"]
    assert [plan[question.id]["sequence_position"] for question in selected] == [1]
    assert all(plan[question.id]["target_difficulty"] is None for question in selected)
    assert all(plan[question.id]["algorithm_version"] == "fixed-sequence-v1" for question in selected)
    assert all(
        plan[question.id]["selection_reason"] == "FIXED_DETERMINISTIC_SEQUENCE"
        for question in selected
    )


def test_fixed_sequence_skips_answered_question_without_reordering():
    first, second = _question(1), _question(2)
    items = [
        SimpleNamespace(question_id=first.id, question=first, position=1, sequence_version="v1"),
        SimpleNamespace(question_id=second.id, question=second, position=2, sequence_version="v1"),
    ]
    answers = [SimpleNamespace(question_id=first.id)]

    selected, _ = QuestionService()._fixed_selection_plan(items, answers)

    assert selected == [second]


def test_fixed_sequence_database_constraints_are_present():
    constraint_names = {item.name for item in ResearchFixedQuestionSequence.__table__.constraints}
    assert "uq_research_fixed_sequence_position" in constraint_names
    assert "uq_research_fixed_sequence_question" in constraint_names


def test_study_question_bank_constraints_are_present():
    constraint_names = {item.name for item in ResearchStudyQuestion.__table__.constraints}
    assert "uq_research_study_questions_question" in constraint_names
    assert "uq_research_study_questions_external" in constraint_names


def test_research_survey_is_unique_per_participant():
    constraint_names = {item.name for item in ResearchSurveyResponse.__table__.constraints}
    assert "uq_research_survey_responses_participation" in constraint_names


def test_research_survey_requires_ten_likert_answers_in_range():
    valid = ResearchSurveySubmit(likert_answers=[1, 2, 3, 4, 5, 1, 2, 3, 4, 5])
    assert len(valid.likert_answers) == 10
    with pytest.raises(ValidationError):
        ResearchSurveySubmit(likert_answers=[3] * 9)
    with pytest.raises(ValidationError):
        ResearchSurveySubmit(likert_answers=[3] * 9 + [6])


def test_research_exam_requires_single_attempt():
    with pytest.raises(ValidationError):
        ExamCreate(
            course_id=uuid4(),
            title="Research PRE",
            assessment_purpose=AssessmentPurpose.RESEARCH_PRE,
            max_attempts=2,
            questions=[ExamQuestionCreate(question_id=uuid4(), position=1)],
        )


def test_research_exam_never_issues_certificate_but_certification_still_does():
    result = SimpleNamespace(passed=True)
    pre = SimpleNamespace(assessment_purpose=AssessmentPurpose.RESEARCH_PRE.value)
    post = SimpleNamespace(assessment_purpose=AssessmentPurpose.RESEARCH_POST.value)
    certification = SimpleNamespace(assessment_purpose=AssessmentPurpose.CERTIFICATION.value)

    assert CertificationService.should_issue_certificate(pre, result) is False
    assert CertificationService.should_issue_certificate(post, result) is False
    assert CertificationService.should_issue_certificate(certification, result) is True


def test_read_only_flag_allows_research_but_blocks_certification(monkeypatch):
    monkeypatch.setattr(certifications.settings, "CERTIFICATION_READ_ONLY", True)

    certifications.require_certification_writable(AssessmentPurpose.RESEARCH_PRE.value)
    certifications.require_certification_writable(AssessmentPurpose.RESEARCH_POST.value)
    with pytest.raises(HTTPException) as exc_info:
        certifications.require_certification_writable(AssessmentPurpose.CERTIFICATION.value)
    assert exc_info.value.status_code == 423


def test_enrollment_contract_rejects_none_group_and_unknown_origin():
    common = {
        "user_id": uuid4(),
        "study_code": "TLMS_ADAPTIVE_PILOT_2026",
        "consent_status": "GRANTED",
    }
    with pytest.raises(ValidationError):
        ResearchEnrollmentRequest(**common, experiment_group="NONE", data_origin="REAL")
    with pytest.raises(ValidationError):
        ResearchEnrollmentRequest(**common, experiment_group="FIXED", data_origin="UNKNOWN")


def test_enrollment_requires_pre_consent_state():
    for consent_status in ("NOT_REQUESTED", "PENDING"):
        payload = ResearchEnrollmentRequest(
            user_id=uuid4(),
            study_code="TLMS_ADAPTIVE_REAL_PILOT_2026",
            experiment_group="ADAPTIVE",
            consent_status=consent_status,
            data_origin="REAL",
        )
        assert payload.consent_status == consent_status
    with pytest.raises(ValidationError):
        ResearchEnrollmentRequest(
            user_id=uuid4(),
            study_code="TLMS_ADAPTIVE_REAL_PILOT_2026",
            experiment_group="ADAPTIVE",
            consent_status="GRANTED",
            data_origin="REAL",
        )


def test_consent_transition_is_explicit_and_terminal_states_cannot_reopen():
    ResearchService._validate_consent_transition("NOT_REQUESTED", "GRANTED")
    ResearchService._validate_consent_transition("PENDING", "GRANTED")
    ResearchService._validate_consent_transition("GRANTED", "WITHDRAWN")
    with pytest.raises(Exception):
        ResearchService._validate_consent_transition("WITHDRAWN", "GRANTED")


def test_real_participant_is_inactive_until_consent_is_granted():
    participation = ResearchParticipation(
        user_id=uuid4(),
        study_code="TLMS_ADAPTIVE_PILOT_2026",
        experiment_group="FIXED",
        data_origin="REAL",
        consent_status="PENDING",
    )
    assert is_active_research_participant(participation) is False
    participation.consent_status = "GRANTED"
    assert is_active_research_participant(participation) is True
    participation.completed_at = datetime.utcnow()
    assert is_active_research_participant(participation) is False


def test_fixed_sequence_payload_rejects_duplicate_questions():
    question_id = uuid4()
    with pytest.raises(ValidationError):
        FixedSequenceConfigure(sequence_version="v1", question_ids=[question_id, question_id])


def test_pre_post_export_is_pseudonymized_and_does_not_compute_learning_gain():
    user_id = uuid4()
    participation = SimpleNamespace(
        user_id=user_id,
        participant_code="P000007",
        study_code="TLMS_ADAPTIVE_PILOT_2026",
        experiment_group="FIXED",
        consent_status="GRANTED",
        data_origin="REAL",
        enrolled_at=datetime.utcnow(),
        completed_at=None,
    )
    exam = SimpleNamespace(id=uuid4(), assessment_purpose=AssessmentPurpose.RESEARCH_PRE.value)
    attempt = SimpleNamespace(
        id=uuid4(), user_id=user_id, started_at=datetime.utcnow(), submitted_at=datetime.utcnow()
    )
    result = SimpleNamespace(
        score=8.0, max_score=10.0, percentage=80.0, passed=True,
        proficiency_level="Proficient", created_at=datetime.utcnow(),
    )

    files = build_export_rows(
        [participation], [], [], [], [],
        [(attempt, result, exam, "TLMS_ADAPTIVE_PILOT_2026")],
    )
    rows, columns = files["06_pre_post_test.csv"]

    assert columns == PRE_POST_COLUMNS
    assert rows[0]["participant_code"] == "P000007"
    assert rows[0]["test_type"] == "PRE"
    assert "learning_gain" not in rows[0]
    assert not {"user_id", "name", "email", "phone", "mssv"} & set(columns)
