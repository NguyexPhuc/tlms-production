"""Idempotent setup for the TLMS real-user adaptive pilot.

This script creates study configuration only. It never enrolls users, grants
consent, or creates attempts/results. A workbook is imported only after all 80
rows pass provenance, licensing, phase-count, and answer validation.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.certification import (
    AssessmentPurpose,
    Course,
    Exam,
    ExamQuestion,
)
from app.models.development import (
    Question,
    QuestionStatus,
    QuestionVerificationStatus,
    ResearchQuestionPhase,
    ResearchStudy,
    ResearchStudyQuestion,
    ResearchStudyStatus,
)
from app.models.task import TaskCreatorType, TaskDifficulty
from app.models.user import MemberLevel


STUDY_CODE = "TLMS_ADAPTIVE_REAL_PILOT_2026"
STUDY_NAME = "TLMS Adaptive Question Real-User Pilot 2026"
STUDY_DESCRIPTION = (
    "Pilot study evaluating the feasibility of collecting longitudinal question "
    "interaction, mastery, difficulty, and adaptive decision data from real TLMS users."
)
QUESTION_BANK_VERSION = "TLMS_OpenLicense_QuestionBank_80_v1"
COURSE_CODE = "TLMS-REAL-PILOT-2026"
EXPECTED_COUNTS = {"PRE": 20, "POST": 20, "TRAIN": 40}
REQUIRED_COLUMNS = {
    "question_id", "set_type", "pair_id", "skill", "topic", "difficulty",
    "question_type", "question_text", "options", "answer_key", "rubric",
    "source_name", "source_url", "source_license", "license_url",
    "adaptation_type", "provenance_status", "content_review_status",
}
OBJECTIVE_TYPES = {"multiple_choice", "single_choice", "true_false", "mcq", "objective"}


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _normalized(value: Any) -> str:
    return _clean(value).upper().replace(" ", "_").replace("-", "_")


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _question_bank_rows(workbook) -> list[dict[str, Any]]:
    sheet_name = "Question_Bank_80"
    if sheet_name not in workbook.sheetnames:
        raise ValueError(f"Missing canonical {sheet_name} sheet")
    worksheet = workbook[sheet_name]
    values = worksheet.iter_rows(values_only=True)
    headers = [_clean(value) for value in next(values, ())]
    missing = sorted(REQUIRED_COLUMNS - set(headers))
    if missing:
        raise ValueError(f"{sheet_name} is missing columns: {', '.join(missing)}")
    rows = [dict(zip(headers, row)) for row in values if any(value is not None for value in row)]
    if len(rows) != sum(EXPECTED_COUNTS.values()):
        raise ValueError(f"{sheet_name} must contain 80 rows, found {len(rows)}")
    return rows


def _parse_options(value: Any) -> dict[str, str] | None:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        raw = value
    else:
        text = _clean(value)
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            raw = {}
            for part in text.replace(";", "\n").splitlines():
                match = re.match(r"^\s*([A-Za-z0-9]+)\s*[.:)]\s*(.+?)\s*$", part)
                if match:
                    raw[match.group(1)] = match.group(2)
    options = {str(key).upper(): _clean(label) for key, label in raw.items() if _clean(label)}
    return options or None


def _answer_keys(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple)):
        values = value
    else:
        text = _clean(value)
        try:
            decoded = json.loads(text)
            values = decoded if isinstance(decoded, list) else [decoded]
        except json.JSONDecodeError:
            values = text.replace(";", ",").split(",")
    return sorted({_clean(item).upper() for item in values if _clean(item)})


def _difficulty(value: Any) -> tuple[TaskDifficulty, float]:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid difficulty: {value!r}") from exc
    if not 1 <= numeric <= 10:
        raise ValueError(f"Difficulty must be in 1..10, found {numeric}")
    label = TaskDifficulty.EASY if numeric <= 3 else TaskDifficulty.MEDIUM if numeric <= 6 else TaskDifficulty.HARD
    return label, numeric


def _skill(value: Any) -> str:
    normalized = _clean(value).casefold().replace(" ", "_").replace("-", "_")
    aliases = {"problem_solving": "problem_solving", "git": "git", "backend": "backend", "database": "database", "frontend": "frontend"}
    if normalized not in aliases:
        raise ValueError(f"Unsupported skill: {value!r}")
    return aliases[normalized]


def _question_type(value: Any) -> str:
    normalized = _clean(value).casefold().replace(" ", "_").replace("-", "_")
    if normalized in OBJECTIVE_TYPES:
        return "multiple_choice"
    if normalized in {"short_answer", "free_text", "text"}:
        return "short_answer"
    raise ValueError(f"Unsupported question_type: {value!r}")


def validate_workbook(path: Path) -> dict[str, list[dict[str, Any]]]:
    if path.name != f"{QUESTION_BANK_VERSION}.xlsx":
        raise ValueError(
            f"Expected {QUESTION_BANK_VERSION}.xlsx, received {path.name}; "
            "do not substitute draft or AI-reviewed workbooks"
        )
    workbook = load_workbook(path, read_only=True, data_only=True)
    rows = _question_bank_rows(workbook)
    phases = {
        phase: [row for row in rows if _normalized(row.get("set_type")) == phase]
        for phase in EXPECTED_COUNTS
    }
    actual_counts = {phase: len(items) for phase, items in phases.items()}
    if actual_counts != EXPECTED_COUNTS:
        raise ValueError(f"Question Bank must contain PRE=20, POST=20, TRAIN=40; found {actual_counts}")
    external_ids: set[str] = set()
    phase_ids: dict[str, set[str]] = {phase: set() for phase in EXPECTED_COUNTS}
    pairs: dict[str, dict[str, str]] = {}
    for phase, rows in phases.items():
        for index, row in enumerate(rows, start=2):
            external_id = _clean(row.get("question_id"))
            if not external_id or external_id in external_ids:
                raise ValueError(f"{phase} row {index}: missing or duplicate question_id {external_id!r}")
            external_ids.add(external_id)
            phase_ids[phase].add(external_id)
            _skill(row.get("skill"))
            _difficulty(row.get("difficulty"))
            if not _clean(row.get("topic")) or not _clean(row.get("question_text")):
                raise ValueError(f"{phase} row {index}: topic and question_text are required")
            if not all(_clean(row.get(key)) for key in ("source_name", "source_url", "source_license", "license_url")):
                raise ValueError(f"{phase} row {index}: source and license metadata are required")
            provenance = _normalized(row.get("provenance_status"))
            review_status = _normalized(row.get("content_review_status"))
            if provenance != "SOURCE_VERIFIED" or review_status != "AI_PRECHECKED":
                raise ValueError(
                    f"{phase} row {index}: requires SOURCE_VERIFIED and AI_PRECHECKED "
                    f"(found {provenance or 'EMPTY'}, {review_status or 'EMPTY'})"
                )
            pair_id = _clean(row.get("pair_id"))
            if phase in {"PRE", "POST"}:
                if not pair_id:
                    raise ValueError(f"{phase} row {index}: pair_id is required")
                pair_phases = pairs.setdefault(pair_id, {})
                if phase in pair_phases:
                    raise ValueError(f"{phase} row {index}: duplicate pair_id {pair_id!r}")
                pair_phases[phase] = external_id
            question_type = _clean(row.get("question_type")).casefold()
            if question_type in OBJECTIVE_TYPES:
                options = _parse_options(row.get("options"))
                answers = _answer_keys(row.get("answer_key"))
                if not options or not answers or not set(answers).issubset(options):
                    raise ValueError(f"{phase} row {index}: objective answer/options are invalid")
            elif not _clean(row.get("rubric")):
                raise ValueError(f"{phase} row {index}: rubric is required")
    overlaps = {
        "PRE/TRAIN": phase_ids["PRE"] & phase_ids["TRAIN"],
        "POST/TRAIN": phase_ids["POST"] & phase_ids["TRAIN"],
        "PRE/POST": phase_ids["PRE"] & phase_ids["POST"],
    }
    if any(overlaps.values()):
        raise ValueError(f"Question IDs overlap across phases: {overlaps}")
    incomplete_pairs = sorted(
        pair_id for pair_id, pair_phases in pairs.items()
        if set(pair_phases) != {"PRE", "POST"}
    )
    if len(pairs) != 20 or incomplete_pairs:
        raise ValueError(
            f"Expected 20 complete PRE/POST pairs, found {len(pairs)}; "
            f"incomplete={incomplete_pairs}"
        )
    return phases


def _git_commit(explicit: str | None = None) -> str | None:
    configured = _clean(explicit or os.getenv("RESEARCH_GIT_COMMIT"))
    if configured:
        if not re.fullmatch(r"[0-9a-fA-F]{7,64}", configured):
            raise ValueError("Research git commit must be a 7-64 character hexadecimal revision")
        return configured.lower()
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


async def ensure_study(
    *,
    workbook_path: Path | None = None,
    git_commit: str | None = None,
) -> dict[str, Any]:
    phases = validate_workbook(workbook_path) if workbook_path else None
    async with AsyncSessionLocal() as db:
        study = (
            await db.execute(select(ResearchStudy).where(ResearchStudy.study_code == STUDY_CODE))
        ).scalar_one_or_none()
        if study is None:
            study = ResearchStudy(
                study_code=STUDY_CODE,
                name=STUDY_NAME,
                description=STUDY_DESCRIPTION,
                study_status=ResearchStudyStatus.DRAFT.value,
                adaptive_algorithm_version="adaptive-v1",
                adaptive_selection_policy_version="question-selection-v1",
                fixed_selection_policy_version="fixed-sequence-v1",
            )
            db.add(study)
            await db.flush()
        else:
            study.name = study.name or STUDY_NAME
            study.description = study.description or STUDY_DESCRIPTION
            study.adaptive_algorithm_version = study.adaptive_algorithm_version or "adaptive-v1"
            study.adaptive_selection_policy_version = (
                study.adaptive_selection_policy_version or "question-selection-v1"
            )
            study.fixed_selection_policy_version = (
                study.fixed_selection_policy_version or "fixed-sequence-v1"
            )

        if phases is None:
            await db.commit()
            return {"study_code": STUDY_CODE, "study_status": study.study_status, "imported": False}

        existing_links = list(
            (
                await db.execute(
                    select(ResearchStudyQuestion).where(ResearchStudyQuestion.study_code == STUDY_CODE)
                )
            ).scalars().all()
        )
        inserted_questions = 0
        inserted_mappings = 0
        reused_questions = 0
        reused_mappings = 0
        updated = 0
        skipped = 0
        if existing_links:
            counts = {phase: 0 for phase in EXPECTED_COUNTS}
            for item in existing_links:
                counts[item.phase] = counts.get(item.phase, 0) + 1
            if counts != EXPECTED_COUNTS:
                raise ValueError(f"Existing study bank is incomplete and will not be overwritten: {counts}")
            existing_by_external_id = {item.external_question_id: item for item in existing_links}
            expected_external_ids = {
                _clean(row["question_id"])
                for rows in phases.values()
                for row in rows
            }
            if set(existing_by_external_id) != expected_external_ids:
                raise ValueError("Existing study bank does not match the supplied workbook")
            reused_questions = len(existing_links)
            reused_mappings = len(existing_links)
            skipped = len(existing_links)
            workbook_rows = {
                _clean(row["question_id"]): row
                for rows in phases.values()
                for row in rows
            }
            for external_id, link in existing_by_external_id.items():
                question = await db.get(Question, link.question_id)
                expected_type = _question_type(workbook_rows[external_id]["question_type"])
                if question.question_type != expected_type:
                    question.question_type = expected_type
                    updated += 1
                    skipped -= 1
        else:
            for phase, rows in phases.items():
                for position, row in enumerate(rows, start=1):
                    difficulty, numeric_difficulty = _difficulty(row["difficulty"])
                    raw_question_type = _clean(row["question_type"]).casefold()
                    question_type = _question_type(row["question_type"])
                    is_objective = raw_question_type in OBJECTIVE_TYPES
                    options = _parse_options(row.get("options")) if is_objective else None
                    answers = _answer_keys(row.get("answer_key")) if is_objective else []
                    adaptation_type = _normalized(row.get("adaptation_type"))
                    expected_answer = (
                        _clean(row.get("answer_key"))
                        if not is_objective
                        else " | ".join(options[key] for key in answers if key in options)
                    )
                    question = Question(
                        title=_clean(row.get("title")) or f"{phase} {_clean(row['question_id'])} - {_clean(row['topic'])}",
                        question=_clean(row["question_text"]),
                        difficulty=difficulty,
                        category="adaptive" if phase == "TRAIN" else f"research_{phase.casefold()}",
                        topic=_clean(row["topic"]),
                        skill_key=_skill(row["skill"]),
                        question_type=question_type,
                        numeric_difficulty=numeric_difficulty,
                        source="research_open_license",
                        source_name=_clean(row["source_name"]),
                        source_url=_clean(row["source_url"]),
                        source_license=_clean(row["source_license"]),
                        is_original=adaptation_type == "ORIGINAL",
                        is_adapted=adaptation_type != "ORIGINAL",
                        verified_status=QuestionVerificationStatus.VERIFIED.value,
                        learning_objective=_clean(row.get("objective")) or None,
                        is_baseline=False,
                        points=int(float(row.get("points") or 1)),
                        expected_duration_minutes=int(float(row.get("expected_duration_minutes") or 5)),
                        target_member_level=MemberLevel.NEW,
                        creator_type=TaskCreatorType.SYSTEM,
                        expected_answer=expected_answer,
                        options=options,
                        correct_option=answers[0] if len(answers) == 1 else None,
                        correct_options=answers or None,
                        feedback=_clean(row.get("rubric")) or None,
                        status=QuestionStatus.ACTIVE,
                    )
                    db.add(question)
                    await db.flush()
                    inserted_questions += 1
                    metadata = {
                        key: _json_value(row.get(key))
                        for key in row
                        if key not in {"question_text", "answer_key", "rubric", "options"}
                        and row.get(key) not in (None, "")
                    }
                    metadata["license_url"] = _clean(row["license_url"])
                    metadata["provenance_status"] = "SOURCE_VERIFIED"
                    metadata["content_review_status"] = "AI_PRECHECKED"
                    db.add(ResearchStudyQuestion(
                        study_code=STUDY_CODE,
                        question_id=question.id,
                        phase=phase,
                        external_question_id=_clean(row["question_id"]),
                        position=position,
                        metadata_json=metadata,
                    ))
                    inserted_mappings += 1
            await db.flush()

        course = (await db.execute(select(Course).where(Course.code == COURSE_CODE))).scalar_one_or_none()
        if course is None:
            course = Course(
                code=COURSE_CODE,
                title=STUDY_NAME,
                description=STUDY_DESCRIPTION,
                skills=["git", "backend", "database", "frontend", "problem_solving"],
                is_published=True,
            )
            db.add(course)
            await db.flush()

        links = list(
            (
                await db.execute(
                    select(ResearchStudyQuestion)
                    .where(ResearchStudyQuestion.study_code == STUDY_CODE)
                    .order_by(ResearchStudyQuestion.phase, ResearchStudyQuestion.position)
                )
            ).scalars().all()
        )
        by_phase = {phase: [item for item in links if item.phase == phase] for phase in EXPECTED_COUNTS}

        async def ensure_exam(phase: str, purpose: AssessmentPurpose) -> Exam:
            exam_id = study.pre_exam_id if phase == "PRE" else study.post_exam_id
            exam = await db.get(Exam, exam_id) if exam_id else None
            if exam is None:
                exam = Exam(
                    course_id=course.id,
                    title=f"TLMS_REAL_PILOT_{phase}_2026",
                    description=f"{phase} assessment for {STUDY_NAME}",
                    duration_minutes=45,
                    pass_percentage=0,
                    max_attempts=1,
                    assessment_purpose=purpose.value,
                    is_published=True,
                )
                db.add(exam)
                await db.flush()
                for item in by_phase[phase]:
                    question = await db.get(Question, item.question_id)
                    answers = question.correct_options or ([question.correct_option] if question.correct_option else None)
                    db.add(ExamQuestion(
                        exam_id=exam.id,
                        question_id=item.question_id,
                        position=item.position,
                        points=1.0,
                        correct_options=answers,
                    ))
            return exam

        pre_exam = await ensure_exam("PRE", AssessmentPurpose.RESEARCH_PRE)
        post_exam = await ensure_exam("POST", AssessmentPurpose.RESEARCH_POST)
        study.pre_exam_id = pre_exam.id
        study.post_exam_id = post_exam.id
        study.git_commit = _git_commit(git_commit) or study.git_commit
        study.question_bank_version = QUESTION_BANK_VERSION
        study.study_status = ResearchStudyStatus.PILOT.value
        await db.commit()
        return {
            "study_code": study.study_code,
            "study_status": study.study_status,
            "pre_exam_id": str(pre_exam.id),
            "post_exam_id": str(post_exam.id),
            "train_question_count": len(by_phase["TRAIN"]),
            "imported": True,
            "inserted": {
                "questions": inserted_questions,
                "mappings": inserted_mappings,
            },
            "updated": updated,
            "reused": {
                "questions": reused_questions,
                "mappings": reused_mappings,
            },
            "skipped": skipped,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path)
    parser.add_argument("--git-commit")
    args = parser.parse_args()
    result = asyncio.run(
        ensure_study(workbook_path=args.workbook, git_commit=args.git_commit)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
