from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.development import MemberSkillProfile, ResearchDataOrigin, ResearchExperimentGroup
from app.services.question import QuestionService


def _question():
    return SimpleNamespace(
        id=uuid4(),
        title="Backend: chống đặt trùng ghế",
        question="Hai request cùng đặt ghế A10 thì backend xử lý thế nào?",
        skill_key="backend",
        category="adaptive",
        topic="concurrency",
        numeric_difficulty=5.0,
    )


def _skill_change(**overrides):
    values = {
        "mastery_before": 50.0,
        "mastery_after": 56.3,
        "confidence_before": 0.3,
        "confidence_after": 0.83,
        "difficulty_before": 3.0,
        "difficulty_after": 3.5,
        "adaptation_reason": "HIGH_RECENT_PERFORMANCE",
    }
    values.update(overrides)
    return values


def _build_attempt(service, question, attempt_number=1, **overrides):
    submitted_at = datetime(2026, 11, 17, 9, 0, 20)
    values = {
        "user_id": uuid4(),
        "question": question,
        "answer_text": "Dùng transaction và unique constraint.",
        "score": 90.0,
        "confidence": 0.8,
        "breakdown": {
            "grading_mode": "ai",
            "ai_provider": "gemini",
            "ai_model": "gemini-2.5-flash",
            "prompt_version": "answer-eval-v1",
        },
        "skill_change": _skill_change(),
        "is_correct": True,
        "attempt_number": attempt_number,
        "submitted_at": submitted_at,
        "started_at": submitted_at - timedelta(seconds=20),
        "roadmap_id": uuid4(),
        "roadmap_week": 3,
        "data_origin": ResearchDataOrigin.UNKNOWN.value,
        "experiment_group": ResearchExperimentGroup.NONE.value,
    }
    values.update(overrides)
    return service._build_attempt_history(**values)


def test_first_and_second_attempt_are_distinct_immutable_snapshots():
    service = QuestionService()
    question = _question()
    first = _build_attempt(service, question, attempt_number=1, answer_text="Lần trả lời đầu")
    second = _build_attempt(service, question, attempt_number=2, answer_text="Lần trả lời thứ hai")

    assert first.attempt_number == 1
    assert second.attempt_number == 2
    assert first.answer_snapshot == "Lần trả lời đầu"
    assert second.answer_snapshot == "Lần trả lời thứ hai"


def test_attempt_snapshots_mastery_difficulty_and_response_time():
    attempt = _build_attempt(QuestionService(), _question())

    assert attempt.mastery_before == 50.0
    assert attempt.mastery_after == 56.3
    assert attempt.difficulty_before == 3.0
    assert attempt.difficulty_after == 3.5
    assert attempt.response_time_seconds == 20.0
    assert attempt.adaptation_reason == "HIGH_RECENT_PERFORMANCE"


def test_attempt_without_roadmap_or_serve_time_keeps_values_null():
    attempt = _build_attempt(
        QuestionService(),
        _question(),
        roadmap_id=None,
        roadmap_week=None,
        started_at=None,
    )

    assert attempt.roadmap_id is None
    assert attempt.roadmap_week is None
    assert attempt.started_at is None
    assert attempt.response_time_seconds is None


def test_local_fallback_is_not_mislabeled_as_ai():
    attempt = _build_attempt(
        QuestionService(),
        _question(),
        breakdown={"grading_mode": "local_fallback"},
    )

    assert attempt.evaluation_method == "LOCAL_FALLBACK"
    assert attempt.ai_score is None
    assert attempt.ai_confidence is None


def test_synthetic_origin_is_preserved():
    attempt = _build_attempt(
        QuestionService(),
        _question(),
        data_origin=ResearchDataOrigin.SYNTHETIC.value,
        experiment_group=ResearchExperimentGroup.ADAPTIVE.value,
    )

    assert attempt.data_origin == "SYNTHETIC"
    assert attempt.data_origin != "REAL"
    assert attempt.experiment_group == "ADAPTIVE"


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


@pytest.mark.asyncio
async def test_skill_profile_logs_actual_increase_branch_without_changing_formula():
    profile = MemberSkillProfile(
        user_id=uuid4(),
        skill_key="backend",
        mastery_score=50.0,
        confidence=0.3,
        current_difficulty=3.0,
        attempts_count=0,
        correct_count=0,
        weak_topics=[],
        strong_topics=[],
    )
    db = SimpleNamespace(execute=AsyncMock(return_value=_ScalarResult(profile)), add=lambda _: None)
    user = SimpleNamespace(id=profile.user_id)
    question = SimpleNamespace(skill_key="backend", category="adaptive", topic="concurrency")

    change = await QuestionService()._update_skill_profile(db, user, question, 90.0, 0.8)

    assert change["mastery_before"] == 50.0
    assert change["mastery_after"] == 55.8
    assert change["difficulty_before"] == 3.0
    assert change["difficulty_after"] == 3.5
    assert change["adaptation_reason"] == "HIGH_RECENT_PERFORMANCE"


@pytest.mark.asyncio
async def test_skill_profile_stable_branch_is_logged():
    profile = MemberSkillProfile(
        user_id=uuid4(),
        skill_key="database",
        mastery_score=60.0,
        confidence=0.5,
        current_difficulty=4.0,
        attempts_count=2,
        correct_count=1,
        weak_topics=[],
        strong_topics=[],
    )
    db = SimpleNamespace(execute=AsyncMock(return_value=_ScalarResult(profile)), add=lambda _: None)
    user = SimpleNamespace(id=profile.user_id)
    question = SimpleNamespace(skill_key="database", category="adaptive", topic="sql_join")

    change = await QuestionService()._update_skill_profile(db, user, question, 70.0, 0.7)

    assert change["difficulty_before"] == change["difficulty_after"]
    assert change["adaptation_reason"] == "STABLE"
