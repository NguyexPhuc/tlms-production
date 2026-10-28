from app.schemas.question import QuestionResponse
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from app.services.question import BASELINE_QUESTIONS, QuestionService, score_text_answer


def test_entry_assessment_has_exactly_five_objective_questions():
    assert len(BASELINE_QUESTIONS) == 5
    for question in BASELINE_QUESTIONS:
        assert set(question["options"]) == {"A", "B", "C", "D"}
        assert question["correct_option"] in question["options"]
        assert question["points"] == 20


def test_public_question_schema_does_not_expose_answer_key():
    assert "options" in QuestionResponse.model_fields
    assert "correct_option" not in QuestionResponse.model_fields
    assert "expected_answer" not in QuestionResponse.model_fields
    assert "accepted_concepts" not in QuestionResponse.model_fields


def test_semantic_fallback_accepts_equivalent_wording():
    concepts = [
        ["khoa chinh dinh danh duy nhat", "primary key unique identifier"],
        ["khoa ngoai tham chieu", "foreign key reference"],
        ["toan ven tham chieu", "referential integrity"],
    ]
    close_score, _, _, _ = score_text_answer(
        "Primary key nhan dien duy nhat tung dong, con foreign key reference sang bang lien quan de giu referential integrity.",
        accepted_concepts=concepts,
    )
    wrong_score, _, _, _ = score_text_answer(
        "Toi se khoi dong lai may chu va thu lai sau.",
        accepted_concepts=concepts,
    )

    assert close_score >= 70
    assert wrong_score < 50


def test_adaptive_selection_returns_five_nearest_high_ability_questions():
    now = datetime.utcnow()
    baseline = [
        SimpleNamespace(
            id=uuid4(),
            is_baseline=True,
            category="baseline",
            skill_key="problem_solving",
            numeric_difficulty=3.0,
            created_at=now,
        )
        for _ in range(5)
    ]
    adaptive = [
        SimpleNamespace(
            id=uuid4(),
            is_baseline=False,
            category="adaptive",
            skill_key="database",
            numeric_difficulty=difficulty,
            created_at=now,
        )
        for difficulty in [2.0, 3.0, 4.0, 5.0, 6.0, 7.5, 8.0]
    ]
    answers = [
        SimpleNamespace(question_id=question.id, final_score=100.0, ai_score=100.0)
        for question in baseline
    ]

    selected = QuestionService()._sort_questions_for_user(baseline + adaptive, answers, [])

    assert len(selected) == 5
    assert selected[0].numeric_difficulty == 7.5
    assert all(question.category == "adaptive" for question in selected)
