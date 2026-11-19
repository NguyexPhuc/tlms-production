"""Export pseudonymized adaptive-learning research datasets using SELECT only."""
import argparse
import asyncio
import csv
import hashlib
from pathlib import Path
from typing import Any, Iterable, Optional
from uuid import UUID

from sqlalchemy import or_, select

from app.core.database import AsyncSessionLocal
from app.models.certification import AssessmentPurpose, Exam, ExamAttempt, ExamResult
from app.models.development import (
    AdaptiveDecisionHistory,
    Question,
    QuestionAttemptHistory,
    ResearchConsentStatus,
    ResearchDataOrigin,
    ResearchParticipation,
    ResearchStudy,
    SkillMasteryHistory,
)


PARTICIPANT_COLUMNS = [
    "participant_code", "study_code", "experiment_group", "consent_status",
    "data_origin", "enrolled_at", "completed_at",
]
QUESTION_COLUMNS = [
    "question_id", "question_type", "topic", "skill_key", "difficulty",
    "numeric_difficulty", "source_name", "source_url", "source_license",
    "is_original", "is_adapted", "parent_question_id", "verified_status",
    "question_version", "created_at",
]
ATTEMPT_COLUMNS = [
    "participant_code", "question_id", "roadmap_week", "skill_key", "topic",
    "question_difficulty", "mastery_before", "mastery_after", "difficulty_before",
    "difficulty_after", "started_at", "submitted_at", "response_time_seconds",
    "response_time_status", "attempt_number", "score", "is_correct",
    "evaluation_method", "ai_score", "ai_confidence", "ai_provider", "ai_model",
    "prompt_version", "manager_score", "final_score", "recent_accuracy",
    "recent_avg_score", "recent_attempts", "recent_response_time_seconds",
    "recent_window_size", "adaptation_reason", "algorithm_version",
    "question_version", "experiment_group", "data_origin", "created_at",
]
MASTERY_COLUMNS = [
    "participant_code", "skill_key", "mastery_before", "mastery_after",
    "confidence_before", "confidence_after", "difficulty_before", "difficulty_after",
    "trigger_type", "algorithm_version", "experiment_group", "data_origin", "created_at",
]
ADAPTATION_COLUMNS = [
    "participant_code", "roadmap_week", "skill_key", "topic", "mastery_at_decision",
    "current_difficulty", "target_difficulty", "recent_accuracy", "recent_avg_score",
    "recent_attempts", "recent_response_time_seconds", "recent_window_size",
    "candidate_question_count", "selected_question_id", "selected_question_difficulty",
    "selection_reason", "baseline_average_score", "ability_difficulty",
    "skill_priority_rank", "algorithm_version", "selection_policy_version",
    "sequence_position", "sequence_version",
    "experiment_group", "data_origin", "created_at",
]
PRE_POST_COLUMNS = [
    "participant_code", "study_code", "test_type", "exam_id", "attempt_id",
    "started_at", "submitted_at", "score", "max_score", "percentage", "passed",
    "proficiency", "created_at",
]
FORBIDDEN_IDENTITY_COLUMNS = {
    "user_id", "name", "email", "phone", "student_id", "mssv", "password",
    "password_hash", "avatar", "zalo_uid", "proof_url", "proof_image",
}


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _question_version(question: Question) -> str:
    payload = "\n".join(
        [
            question.title or "",
            question.question or "",
            question.skill_key or "",
            question.topic or "",
            str(question.numeric_difficulty or ""),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _write_csv(path: Path, columns: list[str], rows: Iterable[dict[str, Any]]) -> None:
    normalized = {column.casefold() for column in columns}
    forbidden = sorted(normalized & FORBIDDEN_IDENTITY_COLUMNS)
    if forbidden:
        raise ValueError(f"Research export contains forbidden identity columns: {forbidden}")
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def filter_participations(
    participations: Iterable[ResearchParticipation],
    *,
    study_code: Optional[str] = None,
    origins: Optional[set[str]] = None,
    include_nonconsented: bool = False,
) -> list[ResearchParticipation]:
    allowed_origins = origins or {ResearchDataOrigin.REAL.value}
    return [
        item
        for item in participations
        if (study_code is None or item.study_code == study_code)
        and _enum_value(item.data_origin) in allowed_origins
        and (
            include_nonconsented
            or _enum_value(item.consent_status) == ResearchConsentStatus.GRANTED.value
        )
    ]


def build_export_rows(
    participations: list[ResearchParticipation],
    questions: list[Question],
    attempts: list[QuestionAttemptHistory],
    mastery_events: list[SkillMasteryHistory],
    decisions: list[AdaptiveDecisionHistory],
    pre_post_records: Optional[list[tuple[ExamAttempt, ExamResult, Exam, str]]] = None,
    *,
    include_answers: bool = False,
) -> dict[str, tuple[list[dict[str, Any]], list[str]]]:
    code_by_user: dict[UUID, str] = {
        item.user_id: item.participant_code for item in participations
    }
    participant_rows = [
        {
            "participant_code": item.participant_code,
            "study_code": item.study_code,
            "experiment_group": _enum_value(item.experiment_group),
            "consent_status": _enum_value(item.consent_status),
            "data_origin": _enum_value(item.data_origin),
            "enrolled_at": item.enrolled_at,
            "completed_at": item.completed_at,
        }
        for item in participations
    ]
    question_rows = [
        {
            "question_id": item.id,
            "question_type": item.question_type,
            "topic": item.topic,
            "skill_key": item.skill_key,
            "difficulty": _enum_value(item.difficulty),
            "numeric_difficulty": item.numeric_difficulty,
            "source_name": item.source_name,
            "source_url": item.source_url,
            "source_license": item.source_license,
            "is_original": item.is_original,
            "is_adapted": item.is_adapted,
            "parent_question_id": item.parent_question_id,
            "verified_status": _enum_value(item.verified_status),
            "question_version": _question_version(item),
            "created_at": item.created_at,
        }
        for item in questions
    ]
    attempt_rows = []
    for item in attempts:
        if item.user_id not in code_by_user:
            continue
        row = {
            "participant_code": code_by_user[item.user_id],
            "question_id": item.question_id,
            "roadmap_week": item.roadmap_week,
            "skill_key": item.skill_key,
            "topic": item.topic,
            "question_difficulty": item.question_difficulty,
            "mastery_before": item.mastery_before,
            "mastery_after": item.mastery_after,
            "difficulty_before": item.difficulty_before,
            "difficulty_after": item.difficulty_after,
            "started_at": item.started_at,
            "submitted_at": item.submitted_at,
            "response_time_seconds": item.response_time_seconds,
            "response_time_status": item.response_time_status,
            "attempt_number": item.attempt_number,
            "score": item.score,
            "is_correct": item.is_correct,
            "evaluation_method": item.evaluation_method,
            "ai_score": item.ai_score,
            "ai_confidence": item.ai_confidence,
            "ai_provider": item.ai_provider,
            "ai_model": item.ai_model,
            "prompt_version": item.prompt_version,
            "manager_score": item.manager_score,
            "final_score": item.final_score,
            "recent_accuracy": item.recent_accuracy,
            "recent_avg_score": item.recent_avg_score,
            "recent_attempts": item.recent_attempts,
            "recent_response_time_seconds": item.recent_response_time_seconds,
            "recent_window_size": item.recent_window_size,
            "adaptation_reason": item.adaptation_reason,
            "algorithm_version": item.algorithm_version,
            "question_version": item.question_version,
            "experiment_group": _enum_value(item.experiment_group),
            "data_origin": _enum_value(item.data_origin),
            "created_at": item.created_at,
        }
        if include_answers:
            row["answer_snapshot"] = item.answer_snapshot
        attempt_rows.append(row)

    mastery_rows = [
        {
            "participant_code": code_by_user[item.user_id],
            "skill_key": item.skill_key,
            "mastery_before": item.mastery_before,
            "mastery_after": item.mastery_after,
            "confidence_before": item.confidence_before,
            "confidence_after": item.confidence_after,
            "difficulty_before": item.difficulty_before,
            "difficulty_after": item.difficulty_after,
            "trigger_type": item.trigger_type,
            "algorithm_version": item.algorithm_version,
            "experiment_group": _enum_value(item.experiment_group),
            "data_origin": _enum_value(item.data_origin),
            "created_at": item.created_at,
        }
        for item in mastery_events
        if item.user_id in code_by_user
    ]
    decision_rows = [
        {
            "participant_code": code_by_user[item.user_id],
            "roadmap_week": item.roadmap_week,
            "skill_key": item.skill_key,
            "topic": item.topic,
            "mastery_at_decision": item.mastery_at_decision,
            "current_difficulty": item.current_difficulty,
            "target_difficulty": item.target_difficulty,
            "recent_accuracy": item.recent_accuracy,
            "recent_avg_score": item.recent_avg_score,
            "recent_attempts": item.recent_attempts,
            "recent_response_time_seconds": item.recent_response_time_seconds,
            "recent_window_size": item.recent_window_size,
            "candidate_question_count": item.candidate_question_count,
            "selected_question_id": item.selected_question_id,
            "selected_question_difficulty": item.selected_question_difficulty,
            "selection_reason": item.selection_reason,
            "baseline_average_score": item.baseline_average_score,
            "ability_difficulty": item.ability_difficulty,
            "skill_priority_rank": item.skill_priority_rank,
            "algorithm_version": item.algorithm_version,
            "selection_policy_version": item.selection_policy_version,
            "sequence_position": getattr(item, "sequence_position", None),
            "sequence_version": getattr(item, "sequence_version", None),
            "experiment_group": _enum_value(item.experiment_group),
            "data_origin": _enum_value(item.data_origin),
            "created_at": item.created_at,
        }
        for item in decisions
        if item.user_id in code_by_user
    ]

    attempt_columns = ATTEMPT_COLUMNS + (["answer_snapshot"] if include_answers else [])
    participation_by_user = {item.user_id: item for item in participations}
    pre_post_rows = []
    for attempt, result, exam, record_study_code in pre_post_records or []:
        participation = participation_by_user.get(attempt.user_id)
        if participation is None or participation.study_code != record_study_code:
            continue
        test_type = {
            AssessmentPurpose.RESEARCH_PRE.value: "PRE",
            AssessmentPurpose.RESEARCH_POST.value: "POST",
        }.get(exam.assessment_purpose)
        if test_type is None:
            continue
        pre_post_rows.append({
            "participant_code": participation.participant_code,
            "study_code": record_study_code,
            "test_type": test_type,
            "exam_id": exam.id,
            "attempt_id": attempt.id,
            "started_at": attempt.started_at,
            "submitted_at": attempt.submitted_at,
            "score": result.score,
            "max_score": result.max_score,
            "percentage": result.percentage,
            "passed": result.passed,
            "proficiency": result.proficiency_level,
            "created_at": result.created_at,
        })
    return {
        "01_participants.csv": (participant_rows, PARTICIPANT_COLUMNS),
        "02_question_bank.csv": (question_rows, QUESTION_COLUMNS),
        "03_question_attempts.csv": (attempt_rows, attempt_columns),
        "04_skill_mastery_history.csv": (mastery_rows, MASTERY_COLUMNS),
        "05_adaptation_history.csv": (decision_rows, ADAPTATION_COLUMNS),
        "06_pre_post_test.csv": (pre_post_rows, PRE_POST_COLUMNS),
    }


async def export_dataset(
    output_dir: Path,
    *,
    study_code: Optional[str] = None,
    origins: Optional[set[str]] = None,
    include_nonconsented: bool = False,
    include_answers: bool = False,
) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    async with AsyncSessionLocal() as db:
        all_participations = list((await db.execute(select(ResearchParticipation))).scalars().all())
        participations = filter_participations(
            all_participations,
            study_code=study_code,
            origins=origins,
            include_nonconsented=include_nonconsented,
        )
        user_ids = [item.user_id for item in participations]
        questions = list((await db.execute(select(Question).order_by(Question.created_at))).scalars().all())
        attempts = list(
            (
                await db.execute(
                    select(QuestionAttemptHistory)
                    .where(QuestionAttemptHistory.user_id.in_(user_ids))
                    .order_by(QuestionAttemptHistory.created_at)
                )
            ).scalars().all()
        )
        mastery_events = list(
            (
                await db.execute(
                    select(SkillMasteryHistory)
                    .where(SkillMasteryHistory.user_id.in_(user_ids))
                    .order_by(SkillMasteryHistory.created_at)
                )
            ).scalars().all()
        )
        decisions = list(
            (
                await db.execute(
                    select(AdaptiveDecisionHistory)
                    .where(AdaptiveDecisionHistory.user_id.in_(user_ids))
                    .order_by(AdaptiveDecisionHistory.created_at)
                )
            ).scalars().all()
        )
        pre_post_records = list(
            (
                await db.execute(
                    select(ExamAttempt, ExamResult, Exam, ResearchStudy.study_code)
                    .join(ExamResult, ExamResult.attempt_id == ExamAttempt.id)
                    .join(Exam, Exam.id == ExamAttempt.exam_id)
                    .join(
                        ResearchStudy,
                        or_(
                            ResearchStudy.pre_exam_id == Exam.id,
                            ResearchStudy.post_exam_id == Exam.id,
                        ),
                    )
                    .where(
                        ExamAttempt.user_id.in_(user_ids),
                        Exam.assessment_purpose.in_([
                            AssessmentPurpose.RESEARCH_PRE.value,
                            AssessmentPurpose.RESEARCH_POST.value,
                        ]),
                    )
                    .order_by(ExamAttempt.started_at)
                )
            ).all()
        )
        db.expunge_all()
        await db.rollback()

    files = build_export_rows(
        participations,
        questions,
        attempts,
        mastery_events,
        decisions,
        pre_post_records,
        include_answers=include_answers,
    )
    for filename, (rows, columns) in files.items():
        _write_csv(output_dir / filename, columns, rows)
    return {filename: len(rows) for filename, (rows, _) in files.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="research_exports", type=Path)
    parser.add_argument("--study-code")
    parser.add_argument(
        "--include-origin",
        action="append",
        choices=[item.value for item in ResearchDataOrigin],
        dest="origins",
        help="Repeat to include non-REAL origins. Default: REAL only.",
    )
    parser.add_argument("--include-nonconsented", action="store_true")
    parser.add_argument("--include-answers", action="store_true")
    args = parser.parse_args()
    counts = asyncio.run(
        export_dataset(
            args.output_dir,
            study_code=args.study_code,
            origins=set(args.origins) if args.origins else None,
            include_nonconsented=args.include_nonconsented,
            include_answers=args.include_answers,
        )
    )
    for filename, count in counts.items():
        print(f"{filename}: {count} rows")


if __name__ == "__main__":
    main()
