from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from app.scripts.export_research_dataset import (
    ADAPTATION_COLUMNS,
    ATTEMPT_COLUMNS,
    FORBIDDEN_IDENTITY_COLUMNS,
    MASTERY_COLUMNS,
    PARTICIPANT_COLUMNS,
    PRE_POST_COLUMNS,
    QUESTION_COLUMNS,
    build_export_rows,
    filter_participations,
)
from app.scripts.export_real_pilot_dataset import SURVEY_COLUMNS, build_survey_row


def _participation(code, consent="GRANTED", origin="REAL", study="PILOT"):
    return SimpleNamespace(
        user_id=uuid4(),
        participant_code=code,
        study_code=study,
        experiment_group="ADAPTIVE",
        consent_status=consent,
        data_origin=origin,
        enrolled_at=datetime(2026, 11, 17),
        completed_at=None,
    )


def test_participant_code_is_reused_across_exports():
    participation = _participation("P000123")

    first = build_export_rows([participation], [], [], [], [])
    second = build_export_rows([participation], [], [], [], [])

    assert first["01_participants.csv"][0][0]["participant_code"] == "P000123"
    assert second["01_participants.csv"][0][0]["participant_code"] == "P000123"


def test_default_filter_excludes_declined_and_demo_records():
    real = _participation("P000001")
    declined = _participation("P000002", consent="DECLINED")
    demo = _participation("P000003", origin="DEMO")

    selected = filter_participations([real, declined, demo])

    assert [item.participant_code for item in selected] == ["P000001"]


def test_debug_filter_can_include_demo_but_still_respects_consent():
    demo = _participation("P000003", origin="DEMO")
    declined_demo = _participation("P000004", consent="DECLINED", origin="DEMO")

    selected = filter_participations(
        [demo, declined_demo], origins={"DEMO"}
    )

    assert [item.participant_code for item in selected] == ["P000003"]


def test_research_csv_headers_never_contain_direct_identity_columns():
    all_columns = {
        *PARTICIPANT_COLUMNS,
        *QUESTION_COLUMNS,
        *ATTEMPT_COLUMNS,
        *MASTERY_COLUMNS,
        *ADAPTATION_COLUMNS,
        *PRE_POST_COLUMNS,
        *SURVEY_COLUMNS,
    }

    assert not ({column.casefold() for column in all_columns} & FORBIDDEN_IDENTITY_COLUMNS)


def test_real_pilot_survey_export_uses_participant_code_only():
    survey = SimpleNamespace(
        likert_answers=[1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
        useful_feedback="Adaptive practice",
        improvement_feedback="More feedback",
        submitted_at=datetime(2026, 11, 19),
    )

    row = build_survey_row(survey, "P000123")

    assert row["participant_code"] == "P000123"
    assert row["likert_10"] == 5
    assert not ({column.casefold() for column in row} & FORBIDDEN_IDENTITY_COLUMNS)
