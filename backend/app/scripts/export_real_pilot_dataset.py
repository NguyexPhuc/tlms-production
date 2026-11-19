"""Export the privacy-safe REAL pilot dataset for manuscript analysis."""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import statistics
import subprocess
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

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
    ResearchQuestionPhase,
    ResearchStudy,
    ResearchStudyQuestion,
    ResearchSurveyResponse,
    SkillMasteryHistory,
)
from app.scripts.research_readiness_check import readiness_report


PARTICIPANT_COLUMNS = [
    "participant_code", "study_code", "experiment_group", "consent_status",
    "data_origin", "enrolled_at", "consent_granted_at", "completed_at",
]
QUESTION_COLUMNS = [
    "question_id", "external_question_id", "phase", "position", "skill", "topic",
    "difficulty", "question_type", "source_name", "source_url", "source_license",
    "license_url", "adaptation_type", "provenance_status", "content_review_status",
]
ATTEMPT_COLUMNS = [
    "participant_code", "question_attempt_id", "question_id", "started_at", "submitted_at",
    "response_time_seconds", "response_time_status", "attempt_number", "skill", "topic",
    "question_difficulty", "score", "is_correct", "evaluation_method", "mastery_before",
    "mastery_after", "difficulty_before", "difficulty_after", "adaptation_reason",
    "algorithm_version", "question_version", "experiment_group", "data_origin",
]
MASTERY_COLUMNS = [
    "participant_code", "skill", "mastery_before", "mastery_after", "confidence_before",
    "confidence_after", "difficulty_before", "difficulty_after", "trigger_type", "trigger_id",
    "algorithm_version", "experiment_group", "data_origin", "created_at",
]
DECISION_COLUMNS = [
    "participant_code", "decision_id", "decision_at", "skill", "topic",
    "mastery_at_decision", "current_difficulty", "target_difficulty", "selected_question_id",
    "selected_question_difficulty", "candidate_count", "selection_reason", "algorithm_version",
    "selection_policy_version", "serve_session_id", "experiment_group", "data_origin",
]
PRE_POST_COLUMNS = [
    "participant_code", "pre_exam_id", "pre_started_at", "pre_submitted_at", "pre_score",
    "pre_max_score", "pre_percentage", "post_exam_id", "post_started_at", "post_submitted_at",
    "post_score", "post_max_score", "post_percentage", "learning_gain",
]
OUTCOME_COLUMNS = [
    "participant_code", "pre_score", "pre_percentage", "post_score", "post_percentage",
    "learning_gain", "train_attempts", "train_correct", "train_accuracy",
    "mean_response_time", "first_mastery", "last_mastery", "mastery_change",
    "first_difficulty", "last_difficulty", "difficulty_change", "active_days",
    "completion_status",
]
SKILL_COLUMNS = [
    "participant_code", "skill", "attempts", "accuracy", "avg_score",
    "avg_question_difficulty", "first_mastery", "last_mastery", "mastery_change",
    "first_difficulty", "last_difficulty", "difficulty_change", "avg_response_time",
]
SURVEY_COLUMNS = ["participant_code", *[f"likert_{index}" for index in range(1, 11)], "most_useful", "needs_improvement", "submitted_at"]
QUALITY_COLUMNS = ["metric", "value", "target", "status"]


def _value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _value(row.get(column)) for column in columns})


def _mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 4) if values else None


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 4) if values else None


def _delta(first: float | None, last: float | None) -> float | None:
    return round(last - first, 4) if first is not None and last is not None else None


def build_survey_row(survey: Any, participant_code: str) -> dict[str, Any]:
    row = {
        "participant_code": participant_code,
        "most_useful": survey.useful_feedback,
        "needs_improvement": survey.improvement_feedback,
        "submitted_at": survey.submitted_at,
    }
    for index, answer in enumerate(survey.likert_answers or [], start=1):
        if index <= 10:
            row[f"likert_{index}"] = answer
    return row


def _git_value(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "NOT AVAILABLE"


async def export_real_pilot(output: Path, study_code: str) -> dict[str, int]:
    output.mkdir(parents=True, exist_ok=True)
    async with AsyncSessionLocal() as db:
        study = (await db.execute(select(ResearchStudy).where(ResearchStudy.study_code == study_code))).scalar_one_or_none()
        if study is None:
            raise ValueError(f"Unknown research study: {study_code}")
        participations = list((await db.execute(select(ResearchParticipation).where(
            ResearchParticipation.study_code == study_code,
            ResearchParticipation.consent_status == ResearchConsentStatus.GRANTED.value,
            ResearchParticipation.data_origin == ResearchDataOrigin.REAL.value,
        ))).scalars().all())
        user_ids = [item.user_id for item in participations]
        code_by_user = {item.user_id: item.participant_code for item in participations}
        start_by_user = {item.user_id: item.consent_granted_at or item.enrolled_at for item in participations}
        links = list((await db.execute(select(ResearchStudyQuestion).where(
            ResearchStudyQuestion.study_code == study_code,
        ).order_by(ResearchStudyQuestion.phase, ResearchStudyQuestion.position))).scalars().all())
        question_ids = [item.question_id for item in links]
        questions = list((await db.execute(select(Question).where(Question.id.in_(question_ids)))).scalars().all()) if question_ids else []
        attempts = list((await db.execute(select(QuestionAttemptHistory).where(
            QuestionAttemptHistory.user_id.in_(user_ids),
            QuestionAttemptHistory.question_id.in_(question_ids),
            QuestionAttemptHistory.data_origin == ResearchDataOrigin.REAL.value,
        ).order_by(QuestionAttemptHistory.submitted_at))).scalars().all()) if user_ids and question_ids else []
        mastery = list((await db.execute(select(SkillMasteryHistory).where(
            SkillMasteryHistory.user_id.in_(user_ids),
            SkillMasteryHistory.data_origin == ResearchDataOrigin.REAL.value,
        ).order_by(SkillMasteryHistory.created_at))).scalars().all()) if user_ids else []
        decisions = list((await db.execute(select(AdaptiveDecisionHistory).where(
            AdaptiveDecisionHistory.user_id.in_(user_ids),
            AdaptiveDecisionHistory.data_origin == ResearchDataOrigin.REAL.value,
        ).order_by(AdaptiveDecisionHistory.created_at))).scalars().all()) if user_ids else []
        exam_records = list((await db.execute(
            select(ExamAttempt, ExamResult, Exam)
            .join(ExamResult, ExamResult.attempt_id == ExamAttempt.id)
            .join(Exam, Exam.id == ExamAttempt.exam_id)
            .where(
                ExamAttempt.user_id.in_(user_ids),
                or_(Exam.id == study.pre_exam_id, Exam.id == study.post_exam_id),
            )
            .order_by(ExamAttempt.started_at)
        )).all()) if user_ids else []
        participation_ids = [item.id for item in participations]
        surveys = list((await db.execute(select(ResearchSurveyResponse).where(
            ResearchSurveyResponse.participation_id.in_(participation_ids),
            ResearchSurveyResponse.study_code == study_code,
        ).order_by(ResearchSurveyResponse.submitted_at))).scalars().all()) if participation_ids else []
        db.expunge_all()
        await db.rollback()

    def in_window(user_id, timestamp) -> bool:
        start = start_by_user.get(user_id)
        return timestamp is not None and (start is None or timestamp >= start)

    attempts = [item for item in attempts if in_window(item.user_id, item.submitted_at)]
    mastery = [item for item in mastery if in_window(item.user_id, item.created_at)]
    decisions = [item for item in decisions if in_window(item.user_id, item.created_at)]
    exam_records = [row for row in exam_records if in_window(row[0].user_id, row[0].submitted_at)]
    participation_by_id = {item.id: item for item in participations}
    surveys = [
        item for item in surveys
        if item.participation_id in participation_by_id
        and in_window(
            participation_by_id[item.participation_id].user_id,
            item.submitted_at,
        )
    ]
    question_by_id = {item.id: item for item in questions}
    link_by_question = {item.question_id: item for item in links}

    participant_rows = [{column: getattr(item, column, None) for column in PARTICIPANT_COLUMNS} for item in participations]
    question_rows = []
    for link in links:
        question = question_by_id.get(link.question_id)
        if question is None:
            continue
        metadata = link.metadata_json or {}
        question_rows.append({
            "question_id": question.id, "external_question_id": link.external_question_id,
            "phase": link.phase, "position": link.position, "skill": question.skill_key,
            "topic": question.topic, "difficulty": question.numeric_difficulty,
            "question_type": question.question_type, "source_name": question.source_name,
            "source_url": question.source_url, "source_license": question.source_license,
            "license_url": metadata.get("license_url"), "adaptation_type": metadata.get("adaptation_type"),
            "provenance_status": metadata.get("provenance_status"),
            "content_review_status": metadata.get("content_review_status"),
        })
    attempt_rows = [{
        "participant_code": code_by_user[item.user_id], "question_attempt_id": item.id,
        "question_id": item.question_id, "started_at": item.started_at, "submitted_at": item.submitted_at,
        "response_time_seconds": item.response_time_seconds, "response_time_status": item.response_time_status,
        "attempt_number": item.attempt_number, "skill": item.skill_key, "topic": item.topic,
        "question_difficulty": item.question_difficulty, "score": item.final_score if item.final_score is not None else item.score,
        "is_correct": item.is_correct, "evaluation_method": item.evaluation_method,
        "mastery_before": item.mastery_before, "mastery_after": item.mastery_after,
        "difficulty_before": item.difficulty_before, "difficulty_after": item.difficulty_after,
        "adaptation_reason": item.adaptation_reason, "algorithm_version": item.algorithm_version,
        "question_version": item.question_version, "experiment_group": item.experiment_group,
        "data_origin": item.data_origin,
    } for item in attempts]
    mastery_rows = [{
        "participant_code": code_by_user[item.user_id], "skill": item.skill_key,
        "mastery_before": item.mastery_before, "mastery_after": item.mastery_after,
        "confidence_before": item.confidence_before, "confidence_after": item.confidence_after,
        "difficulty_before": item.difficulty_before, "difficulty_after": item.difficulty_after,
        "trigger_type": item.trigger_type, "trigger_id": item.trigger_id,
        "algorithm_version": item.algorithm_version, "experiment_group": item.experiment_group,
        "data_origin": item.data_origin, "created_at": item.created_at,
    } for item in mastery]
    decision_rows = [{
        "participant_code": code_by_user[item.user_id], "decision_id": item.id,
        "decision_at": item.created_at, "skill": item.skill_key, "topic": item.topic,
        "mastery_at_decision": item.mastery_at_decision, "current_difficulty": item.current_difficulty,
        "target_difficulty": item.target_difficulty, "selected_question_id": item.selected_question_id,
        "selected_question_difficulty": item.selected_question_difficulty,
        "candidate_count": item.candidate_question_count, "selection_reason": item.selection_reason,
        "algorithm_version": item.algorithm_version, "selection_policy_version": item.selection_policy_version,
        "serve_session_id": item.question_serve_session_id, "experiment_group": item.experiment_group,
        "data_origin": item.data_origin,
    } for item in decisions]

    exam_by_user: dict[Any, dict[str, tuple[Any, Any]]] = defaultdict(dict)
    for exam_attempt, result, exam in exam_records:
        phase = "PRE" if exam.assessment_purpose == AssessmentPurpose.RESEARCH_PRE.value else "POST"
        exam_by_user[exam_attempt.user_id][phase] = (exam_attempt, result)
    pre_post_rows = []
    for participation in participations:
        pre = exam_by_user[participation.user_id].get("PRE")
        post = exam_by_user[participation.user_id].get("POST")
        pre_result = pre[1] if pre else None
        post_result = post[1] if post else None
        pre_post_rows.append({
            "participant_code": participation.participant_code,
            "pre_exam_id": pre_result.exam_id if pre_result else None,
            "pre_started_at": pre[0].started_at if pre else None,
            "pre_submitted_at": pre[0].submitted_at if pre else None,
            "pre_score": pre_result.score if pre_result else None,
            "pre_max_score": pre_result.max_score if pre_result else None,
            "pre_percentage": pre_result.percentage if pre_result else None,
            "post_exam_id": post_result.exam_id if post_result else None,
            "post_started_at": post[0].started_at if post else None,
            "post_submitted_at": post[0].submitted_at if post else None,
            "post_score": post_result.score if post_result else None,
            "post_max_score": post_result.max_score if post_result else None,
            "post_percentage": post_result.percentage if post_result else None,
            "learning_gain": _delta(pre_result.percentage if pre_result else None, post_result.percentage if post_result else None),
        })

    attempts_by_user: dict[Any, list[Any]] = defaultdict(list)
    mastery_by_user: dict[Any, list[Any]] = defaultdict(list)
    for item in attempts: attempts_by_user[item.user_id].append(item)
    for item in mastery: mastery_by_user[item.user_id].append(item)
    outcome_rows = []
    for participation in participations:
        user_attempts = attempts_by_user[participation.user_id]
        user_mastery = mastery_by_user[participation.user_id]
        scores = [float(item.final_score if item.final_score is not None else item.score) for item in user_attempts if (item.final_score if item.final_score is not None else item.score) is not None]
        valid_times = [float(item.response_time_seconds) for item in user_attempts if item.response_time_status == "VALID" and item.response_time_seconds is not None]
        pre_post = next(row for row in pre_post_rows if row["participant_code"] == participation.participant_code)
        first_mastery = user_mastery[0].mastery_before if user_mastery else None
        last_mastery = user_mastery[-1].mastery_after if user_mastery else None
        first_difficulty = user_mastery[0].difficulty_before if user_mastery else None
        last_difficulty = user_mastery[-1].difficulty_after if user_mastery else None
        active_days = len({item.submitted_at.date() for item in user_attempts})
        completed = bool(pre_post["pre_percentage"] is not None and len(user_attempts) >= 20 and pre_post["post_percentage"] is not None)
        outcome_rows.append({
            "participant_code": participation.participant_code, "pre_score": pre_post["pre_score"],
            "pre_percentage": pre_post["pre_percentage"], "post_score": pre_post["post_score"],
            "post_percentage": pre_post["post_percentage"], "learning_gain": pre_post["learning_gain"],
            "train_attempts": len(user_attempts), "train_correct": sum(item.is_correct is True for item in user_attempts),
            "train_accuracy": round(sum(item.is_correct is True for item in user_attempts) / len(user_attempts), 4) if user_attempts else None,
            "mean_response_time": _mean(valid_times), "first_mastery": first_mastery,
            "last_mastery": last_mastery, "mastery_change": _delta(first_mastery, last_mastery),
            "first_difficulty": first_difficulty, "last_difficulty": last_difficulty,
            "difficulty_change": _delta(first_difficulty, last_difficulty), "active_days": active_days,
            "completion_status": "PILOT_COMPLETED" if completed else "PILOT_INCOMPLETE",
        })

    skill_rows = []
    grouped: dict[tuple[Any, str], list[Any]] = defaultdict(list)
    for item in attempts: grouped[(item.user_id, item.skill_key or "unknown")].append(item)
    for (user_id, skill), items in grouped.items():
        skill_mastery = [item for item in mastery_by_user[user_id] if item.skill_key == skill]
        scores = [float(item.final_score if item.final_score is not None else item.score) for item in items if (item.final_score if item.final_score is not None else item.score) is not None]
        difficulties = [float(item.question_difficulty) for item in items if item.question_difficulty is not None]
        times = [float(item.response_time_seconds) for item in items if item.response_time_status == "VALID" and item.response_time_seconds is not None]
        first_mastery = skill_mastery[0].mastery_before if skill_mastery else None
        last_mastery = skill_mastery[-1].mastery_after if skill_mastery else None
        first_difficulty = skill_mastery[0].difficulty_before if skill_mastery else None
        last_difficulty = skill_mastery[-1].difficulty_after if skill_mastery else None
        skill_rows.append({
            "participant_code": code_by_user[user_id], "skill": skill, "attempts": len(items),
            "accuracy": round(sum(item.is_correct is True for item in items) / len(items), 4),
            "avg_score": _mean(scores), "avg_question_difficulty": _mean(difficulties),
            "first_mastery": first_mastery, "last_mastery": last_mastery,
            "mastery_change": _delta(first_mastery, last_mastery), "first_difficulty": first_difficulty,
            "last_difficulty": last_difficulty, "difficulty_change": _delta(first_difficulty, last_difficulty),
            "avg_response_time": _mean(times),
        })

    survey_rows = []
    for survey in surveys:
        participation = participation_by_id[survey.participation_id]
        survey_rows.append(build_survey_row(survey, participation.participant_code))

    valid_response = sum(item.response_time_status == "VALID" for item in attempts)
    quality_rows = [
        {"metric": "REAL participants", "value": len(participations), "target": ">=5", "status": "PASS" if len(participations) >= 5 else "NOT MET"},
        {"metric": "Immutable REAL attempts", "value": len(attempts), "target": ">=100", "status": "PASS" if len(attempts) >= 100 else "NOT MET"},
        {"metric": "Mastery history", "value": len(mastery), "target": ">0", "status": "PASS" if mastery else "NOT MET"},
        {"metric": "Adaptive decisions", "value": len(decisions), "target": ">0", "status": "PASS" if decisions else "NOT MET"},
        {"metric": "PRE complete", "value": sum(row["pre_percentage"] is not None for row in pre_post_rows), "target": ">=5", "status": "PASS" if sum(row["pre_percentage"] is not None for row in pre_post_rows) >= 5 else "NOT MET"},
        {"metric": "POST complete", "value": sum(row["post_percentage"] is not None for row in pre_post_rows), "target": ">=5", "status": "PASS" if sum(row["post_percentage"] is not None for row in pre_post_rows) >= 5 else "NOT MET"},
        {"metric": "Valid response-time coverage", "value": round(valid_response / len(attempts) * 100, 2) if attempts else 0, "target": ">=80%", "status": "PASS" if attempts and valid_response / len(attempts) >= .8 else "NOT MET"},
    ]

    files = {
        "01_participants.csv": (PARTICIPANT_COLUMNS, participant_rows),
        "02_question_bank.csv": (QUESTION_COLUMNS, question_rows),
        "03_question_attempts.csv": (ATTEMPT_COLUMNS, attempt_rows),
        "04_skill_mastery_history.csv": (MASTERY_COLUMNS, mastery_rows),
        "05_adaptive_decisions.csv": (DECISION_COLUMNS, decision_rows),
        "06_pre_post_results.csv": (PRE_POST_COLUMNS, pre_post_rows),
        "07_participant_outcomes.csv": (OUTCOME_COLUMNS, outcome_rows),
        "08_participant_skill_outcomes.csv": (SKILL_COLUMNS, skill_rows),
        "09_survey.csv": (SURVEY_COLUMNS, survey_rows),
        "10_data_quality.csv": (QUALITY_COLUMNS, quality_rows),
    }
    for filename, (columns, rows) in files.items(): _write_csv(output / filename, columns, rows)

    readiness = await readiness_report(study_code)
    manifest_lines = ["# TLMS Real Pilot Dataset Manifest", "", f"Study: `{study_code}`", "", "| File | Rows | PII |", "| --- | ---: | --- |"]
    for filename, (_, rows) in files.items(): manifest_lines.append(f"| `{filename}` | {len(rows)} | Removed |")
    (output / "00_manifest.md").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    (output / "00_codebook.md").write_text(
        "# Codebook\n\nAll identifiers are research participant codes. Percentages use 0-100; "
        "mastery uses 0-100; difficulty uses 1-10; response time is seconds. "
        "Learning/mastery/difficulty change fields are derived as last minus first. "
        "No raw identity or answer text is exported.\n",
        encoding="utf-8",
    )
    (output / "11_system_method_snapshot.md").write_text(
        "# System Method Snapshot\n\n"
        f"- Git commit: `{_git_value('rev-parse', 'HEAD')}`\n"
        f"- Git branch: `{_git_value('branch', '--show-current')}`\n"
        f"- Algorithm: `{study.adaptive_algorithm_version}`\n"
        f"- Selection policy: `{study.adaptive_selection_policy_version}`\n"
        "- Ability mapping: <50 -> 3.0; <80 -> 5.0; otherwise 7.5.\n"
        "- Target difficulty: 0.6 * ability difficulty + 0.4 * current skill difficulty.\n"
        "- Ranking: weak-skill priority, absolute target gap, creation time.\n",
        encoding="utf-8",
    )
    pre_values = [row["pre_percentage"] for row in pre_post_rows if row["pre_percentage"] is not None]
    post_values = [row["post_percentage"] for row in pre_post_rows if row["post_percentage"] is not None]
    gains = [row["learning_gain"] for row in pre_post_rows if row["learning_gain"] is not None]
    summary = f"""# Pilot Summary

- Registered/enrolled REAL participants: {len(participations)}
- Consent granted: {len(participations)}
- PRE completed: {len(pre_values)}
- TRAIN completed (>=20): {sum(row['train_attempts'] >= 20 for row in outcome_rows)}
- POST completed: {len(post_values)}
- Pilot completed: {sum(row['completion_status'] == 'PILOT_COMPLETED' for row in outcome_rows)}
- Survey completed: {len(survey_rows)}
- REAL question attempts: {len(attempts)}
- REAL mastery-history rows: {len(mastery)}
- REAL adaptive decisions: {len(decisions)}
- Valid response times: {valid_response}
- Invalid/missing response times: {len(attempts) - valid_response}
- Skills covered: {len({row['skill'] for row in skill_rows})}
- Question count used: {len({item.question_id for item in attempts})}
- PRE mean/median: {_mean(pre_values) if pre_values else 'NOT AVAILABLE'} / {_median(pre_values) if pre_values else 'NOT AVAILABLE'}
- POST mean/median: {_mean(post_values) if post_values else 'NOT AVAILABLE'} / {_median(post_values) if post_values else 'NOT AVAILABLE'}
- Learning gain mean/median: {_mean(gains) if gains else 'NOT AVAILABLE'} / {_median(gains) if gains else 'NOT AVAILABLE'}

This observational pilot export does not support causal or Adaptive-versus-Fixed superiority claims.
"""
    (output / "12_pilot_summary.md").write_text(summary, encoding="utf-8")
    (output / "13_pilot_readiness_report.md").write_text(
        "# Pilot Readiness Report\n\n```json\n" + json.dumps(readiness, ensure_ascii=False, indent=2, default=_value) + "\n```\n",
        encoding="utf-8",
    )
    return {filename: len(rows) for filename, (_, rows) in files.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-code", required=True)
    parser.add_argument("--output", type=Path, default=Path("research_real_pilot_export"))
    args = parser.parse_args()
    counts = asyncio.run(export_real_pilot(args.output, args.study_code))
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
