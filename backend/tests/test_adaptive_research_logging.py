from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.development import (
    AdaptiveDecisionHistory,
    MemberSkillProfile,
    ResearchDataOrigin,
    ResearchExperimentGroup,
    ResponseTimeStatus,
)
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
    assert attempt.response_time_status == ResponseTimeStatus.VALID.value
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
    assert attempt.response_time_status == ResponseTimeStatus.MISSING_START.value


def test_response_time_records_eighty_seconds_without_rounding_away_observation():
    submitted_at = datetime(2026, 11, 17, 12, 1, 20)
    attempt = _build_attempt(
        QuestionService(),
        _question(),
        submitted_at=submitted_at,
        started_at=datetime(2026, 11, 17, 12, 0, 0),
    )

    assert attempt.response_time_seconds == 80.0
    assert attempt.response_time_status == ResponseTimeStatus.VALID.value


def test_negative_response_time_is_rejected_and_marked_invalid_clock():
    submitted_at = datetime(2026, 11, 17, 12, 0, 0)
    attempt = _build_attempt(
        QuestionService(),
        _question(),
        submitted_at=submitted_at,
        started_at=datetime(2026, 11, 17, 12, 0, 1),
    )

    assert attempt.response_time_seconds is None
    assert attempt.response_time_status == ResponseTimeStatus.INVALID_CLOCK.value


def test_long_response_time_keeps_raw_duration_and_marks_outlier():
    submitted_at = datetime(2026, 11, 17, 16, 0, 1)
    attempt = _build_attempt(
        QuestionService(),
        _question(),
        submitted_at=submitted_at,
        started_at=datetime(2026, 11, 17, 12, 0, 0),
    )

    assert attempt.response_time_seconds == 14401.0
    assert attempt.response_time_status == ResponseTimeStatus.OUTLIER.value


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


@pytest.mark.asyncio
async def test_new_skill_profile_initializes_difficulty_before_stable_update():
    added = []
    db = SimpleNamespace(
        execute=AsyncMock(return_value=_ScalarResult(None)),
        add=added.append,
    )
    user = SimpleNamespace(id=uuid4())
    question = SimpleNamespace(skill_key="frontend", category="adaptive", topic="state")

    change = await QuestionService()._update_skill_profile(db, user, question, 60.0, 0.45)

    assert len(added) == 1
    assert change["difficulty_before"] == 3.0
    assert change["difficulty_after"] == 3.0
    assert change["adaptation_reason"] == "STABLE"


def test_selection_plan_snapshots_actual_selector_inputs_without_fake_recent_metrics():
    now = datetime(2026, 11, 17, 10, 0, 0)
    baseline = SimpleNamespace(
        id=uuid4(), is_baseline=True, category="baseline", skill_key="database",
        topic="baseline", numeric_difficulty=3.0, created_at=now,
    )
    adaptive = SimpleNamespace(
        id=uuid4(), is_baseline=False, category="adaptive", skill_key="backend",
        topic="concurrency", numeric_difficulty=5.0, created_at=now,
    )
    answers = [SimpleNamespace(question_id=baseline.id, final_score=70.0, ai_score=70.0)]
    profile = SimpleNamespace(
        skill_key="backend", mastery_score=45.0, confidence=0.7, current_difficulty=4.0,
    )

    selected, plan = QuestionService()._selection_plan(
        [baseline, adaptive], answers, [profile]
    )
    snapshot = plan[adaptive.id]

    assert selected == [adaptive]
    assert snapshot["candidate_question_count"] == 1
    assert snapshot["baseline_average_score"] == 70.0
    assert snapshot["current_difficulty"] == 4.0
    assert snapshot["target_difficulty"] == pytest.approx(4.6)
    assert snapshot["selected_question_difficulty"] == 5.0
    assert snapshot["recent_accuracy"] is None
    assert snapshot["selection_reason"] == "WEAK_SKILL_PRIORITY_THEN_TARGET_DIFFICULTY"


@pytest.mark.asyncio
async def test_new_serve_creates_selection_decision_but_refresh_does_not_duplicate():
    service = QuestionService()
    user = SimpleNamespace(id=uuid4())
    question_id = uuid4()
    session = SimpleNamespace(id=uuid4(), started_at=datetime(2026, 11, 17, 10, 0, 0))
    added = []
    db = SimpleNamespace(add=added.append, flush=AsyncMock())
    service._research_context = AsyncMock(return_value=("P000001", "REAL", "ADAPTIVE"))
    service._roadmap_snapshot = AsyncMock(return_value=(uuid4(), 3))
    plan = {
        question_id: {
            "skill_key": "backend",
            "topic": "concurrency",
            "mastery_at_decision": 45.0,
            "current_difficulty": 4.0,
            "target_difficulty": 4.6,
            "candidate_question_count": 7,
            "selected_question_difficulty": 5.0,
            "selection_reason": "WEAK_SKILL_PRIORITY_THEN_TARGET_DIFFICULTY",
        }
    }

    await service._record_selection_decisions(
        db, user, plan, {question_id: (session, True)}
    )
    await service._record_selection_decisions(
        db, user, plan, {question_id: (session, False)}
    )

    decisions = [item for item in added if isinstance(item, AdaptiveDecisionHistory)]
    assert len(decisions) == 1
    assert decisions[0].participant_code == "P000001"
    assert decisions[0].selected_question_id == question_id
    assert decisions[0].candidate_question_count == 7
