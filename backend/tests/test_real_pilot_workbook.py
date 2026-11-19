from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from app.scripts.setup_real_pilot import validate_workbook


HEADERS = [
    "question_id", "set_type", "pair_id", "skill", "topic", "difficulty",
    "question_type", "question_text", "options", "answer_key", "rubric",
    "source_name", "source_url", "source_license", "license_url",
    "adaptation_type", "provenance_status", "content_review_status",
    "human_spotcheck", "pilot_eligible",
]
SKILLS = ["Git", "Backend", "Database", "Frontend", "Problem Solving"]


def _write_workbook(tmp_path: Path) -> Path:
    path = tmp_path / "TLMS_OpenLicense_QuestionBank_80_v1.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Question_Bank_80"
    worksheet.append(HEADERS)
    for phase, count in (("PRE", 20), ("POST", 20), ("TRAIN", 40)):
        for position in range(count):
            pair_id = f"PAIR-{position + 1:02d}" if phase != "TRAIN" else ""
            worksheet.append([
                f"{phase}-{position + 1:02d}", phase, pair_id,
                SKILLS[position % len(SKILLS)], "Topic", 4, "MCQ", "Question?",
                "A. First\nB. Second\nC. Third\nD. Fourth", "A", "Answer A",
                "Open course", "https://example.edu/course", "CC BY-NC-SA 4.0",
                "https://creativecommons.org/licenses/by-nc-sa/4.0/",
                "CONCEPT_ADAPTED", "SOURCE_VERIFIED", "AI_PRECHECKED",
                "PENDING", "NO",
            ])
    workbook.save(path)
    return path


def test_workbook_accepts_ai_precheck_without_human_signoff(tmp_path):
    phases = validate_workbook(_write_workbook(tmp_path))

    assert {phase: len(rows) for phase, rows in phases.items()} == {
        "PRE": 20,
        "POST": 20,
        "TRAIN": 40,
    }


def test_workbook_rejects_missing_ai_precheck(tmp_path):
    path = _write_workbook(tmp_path)
    workbook = load_workbook(path)
    worksheet = workbook["Question_Bank_80"]
    worksheet.cell(row=2, column=HEADERS.index("content_review_status") + 1).value = "PENDING"
    workbook.save(path)

    with pytest.raises(ValueError, match="SOURCE_VERIFIED and AI_PRECHECKED"):
        validate_workbook(path)


def test_workbook_rejects_question_id_overlap(tmp_path):
    path = _write_workbook(tmp_path)
    workbook = load_workbook(path)
    worksheet = workbook["Question_Bank_80"]
    worksheet.cell(row=22, column=1).value = "PRE-01"
    workbook.save(path)

    with pytest.raises(ValueError, match="missing or duplicate question_id"):
        validate_workbook(path)
