"""Export pseudonymized adaptive-learning research datasets using SELECT only."""
import argparse
import asyncio
import csv
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.development import (
    Question,
    QuestionAttemptHistory,
    ResearchDataOrigin,
    ResearchExperimentGroup,
    ResearchParticipation,
    SkillMasteryHistory,
)


def _write_csv(path: Path, columns: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


async def export_dataset(output_dir: Path) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    async with AsyncSessionLocal() as db:
        participations = list(
            (await db.execute(select(ResearchParticipation))).scalars().all()
        )
        questions = list(
            (await db.execute(select(Question).order_by(Question.created_at))).scalars().all()
        )
        attempts = list(
            (
                await db.execute(
                    select(QuestionAttemptHistory).order_by(QuestionAttemptHistory.created_at)
                )
            ).scalars().all()
        )
        mastery_events = list(
            (
                await db.execute(
                    select(SkillMasteryHistory).order_by(SkillMasteryHistory.created_at)
                )
            ).scalars().all()
        )
        # This exporter must never persist operational changes.
        db.expunge_all()
        await db.rollback()

    user_ids = sorted(
        {
            *[item.user_id for item in participations],
            *[item.user_id for item in attempts],
            *[item.user_id for item in mastery_events],
        },
        key=str,
    )
    participant_ids = {user_id: f"P{index:03d}" for index, user_id in enumerate(user_ids, start=1)}
    participation_by_user = {item.user_id: item for item in participations}

    participant_rows = []
    for user_id in user_ids:
        participation = participation_by_user.get(user_id)
        related_attempt = next((item for item in attempts if item.user_id == user_id), None)
        participant_rows.append(
            {
                "participant_id": participant_ids[user_id],
                "experiment_group": (
                    participation.experiment_group
                    if participation
                    else related_attempt.experiment_group if related_attempt else ResearchExperimentGroup.NONE.value
                ),
                "study_code": participation.study_code if participation else None,
                "enrolled_at": participation.enrolled_at if participation else None,
                "completed_at": participation.completed_at if participation else None,
                "consent_status": participation.consent_status if participation else None,
                "data_origin": (
                    participation.data_origin
                    if participation
                    else related_attempt.data_origin if related_attempt else ResearchDataOrigin.UNKNOWN.value
                ),
            }
        )

    question_rows = [
        {
            "question_id": item.id,
            "topic": item.topic,
            "skill": item.skill_key,
            "question_type": item.question_type,
            "difficulty": item.difficulty.value if hasattr(item.difficulty, "value") else item.difficulty,
            "numeric_difficulty": item.numeric_difficulty,
            "source": item.source,
            "source_license": None,
            "objective": item.learning_objective,
        }
        for item in questions
    ]

    attempt_rows = [
        {
            "participant_id": participant_ids[item.user_id],
            "question_id": item.question_id,
            "roadmap_week": item.roadmap_week,
            "skill": item.skill_key,
            "topic": item.topic,
            "question_difficulty": item.question_difficulty,
            "mastery_before": item.mastery_before,
            "difficulty_before": item.difficulty_before,
            "started_at": item.started_at,
            "submitted_at": item.submitted_at,
            "response_time_seconds": item.response_time_seconds,
            "attempt_number": item.attempt_number,
            "score": item.score,
            "is_correct": item.is_correct,
            "evaluation_method": item.evaluation_method,
            "ai_confidence": item.ai_confidence,
            "mastery_after": item.mastery_after,
            "difficulty_after": item.difficulty_after,
            "adaptation_reason": item.adaptation_reason,
            "algorithm_version": item.algorithm_version,
            "data_origin": item.data_origin,
            "created_at": item.created_at,
        }
        for item in attempts
    ]

    mastery_rows = [
        {
            "participant_id": participant_ids[item.user_id],
            "skill": item.skill_key,
            "mastery_before": item.mastery_before,
            "mastery_after": item.mastery_after,
            "confidence_before": item.confidence_before,
            "confidence_after": item.confidence_after,
            "difficulty_before": item.difficulty_before,
            "difficulty_after": item.difficulty_after,
            "trigger_type": item.trigger_type,
            "algorithm_version": item.algorithm_version,
            "created_at": item.created_at,
        }
        for item in mastery_events
    ]

    adaptation_rows = [
        {
            "participant_id": participant_ids[item.user_id],
            "skill": item.skill_key,
            "question_id": item.question_id,
            "previous_difficulty": item.difficulty_before,
            "new_difficulty": item.difficulty_after,
            "previous_mastery": item.mastery_before,
            "new_mastery": item.mastery_after,
            "recent_accuracy": None,
            "recent_avg_score": None,
            "recent_attempts": None,
            "recent_response_time": None,
            "adaptation_reason": item.adaptation_reason,
            "algorithm_version": item.algorithm_version,
            "created_at": item.created_at,
        }
        for item in attempts
    ]

    files = {
        "01_participants.csv": (participant_rows, list(participant_rows[0]) if participant_rows else [
            "participant_id", "experiment_group", "study_code", "enrolled_at", "completed_at", "consent_status", "data_origin"
        ]),
        "02_question_bank.csv": (question_rows, [
            "question_id", "topic", "skill", "question_type", "difficulty", "numeric_difficulty", "source", "source_license", "objective"
        ]),
        "03_question_attempts.csv": (attempt_rows, [
            "participant_id", "question_id", "roadmap_week", "skill", "topic", "question_difficulty", "mastery_before",
            "difficulty_before", "started_at", "submitted_at", "response_time_seconds", "attempt_number", "score", "is_correct",
            "evaluation_method", "ai_confidence", "mastery_after", "difficulty_after", "adaptation_reason", "algorithm_version",
            "data_origin", "created_at"
        ]),
        "04_skill_mastery_history.csv": (mastery_rows, [
            "participant_id", "skill", "mastery_before", "mastery_after", "confidence_before", "confidence_after",
            "difficulty_before", "difficulty_after", "trigger_type", "algorithm_version", "created_at"
        ]),
        "05_adaptation_history.csv": (adaptation_rows, [
            "participant_id", "skill", "question_id", "previous_difficulty", "new_difficulty", "previous_mastery", "new_mastery",
            "recent_accuracy", "recent_avg_score", "recent_attempts", "recent_response_time", "adaptation_reason", "algorithm_version", "created_at"
        ]),
    }
    for filename, (rows, columns) in files.items():
        _write_csv(output_dir / filename, columns, rows)
    return {filename: len(rows) for filename, (rows, _) in files.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="research_exports", type=Path)
    args = parser.parse_args()
    counts = asyncio.run(export_dataset(args.output_dir))
    for filename, count in counts.items():
        print(f"{filename}: {count} rows")


if __name__ == "__main__":
    main()
