from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.development import ResearchParticipation
from app.models.user import User, UserRole, UserStatus
from app.schemas.research import ResearchEnrollmentRequest
from app.scripts.enroll_real_pilot_participants import (
    InputAccount,
    _lookup_user,
    classify_user,
    mask_identifier,
    read_allowlist,
)
from app.services.research import ResearchService


STUDY = "TLMS_ADAPTIVE_REAL_PILOT_2026"


def _account(**overrides):
    values = {
        "row_number": 2,
        "identifier_type": "email",
        "identifier": "real.user@example.com",
        "allow_mentor": False,
    }
    values.update(overrides)
    return InputAccount(**values)


def _user(**overrides):
    values = {
        "id": uuid4(),
        "s4h_user_id": f"local:{uuid4()}",
        "email": "real.user@example.com",
        "roles": [UserRole.CANDIDATE.value],
        "status": UserStatus.ACTIVE,
    }
    values.update(overrides)
    return User(**values)


def test_selected_real_candidate_is_ready_and_identifier_is_masked():
    plan = classify_user(_account(), _user(), None, STUDY)

    assert plan.enrollment_status == "READY_TO_ENROLL"
    assert plan.consent_status == "NOT_REQUESTED"
    assert plan.data_origin == "REAL"
    assert mask_identifier("email", "person@example.com") == "pe***@example.com"


def test_inactive_user_is_rejected():
    plan = classify_user(
        _account(), _user(status=UserStatus.INACTIVE), None, STUDY
    )
    assert plan.enrollment_status == "INACTIVE"


def test_admin_and_explicit_test_accounts_are_rejected():
    admin = classify_user(
        _account(), _user(roles=[UserRole.ADMIN.value]), None, STUDY
    )
    test_account = classify_user(
        _account(identifier="test-user@example.com"),
        _user(email="test-user@example.com"),
        None,
        STUDY,
    )

    assert admin.enrollment_status == "INELIGIBLE_ROLE"
    assert test_account.enrollment_status == "TEST_OR_DEMO"


def test_mentor_requires_explicit_row_permission():
    mentor = _user(roles=[UserRole.MENTOR.value])

    blocked = classify_user(_account(), mentor, None, STUDY)
    allowed = classify_user(_account(allow_mentor=True), mentor, None, STUDY)

    assert blocked.enrollment_status == "INELIGIBLE_ROLE"
    assert allowed.enrollment_status == "READY_TO_ENROLL"


def test_already_enrolled_is_skipped_without_changing_stable_fields():
    user = _user()
    participation = ResearchParticipation(
        user_id=user.id,
        participant_code="P000099",
        study_code=STUDY,
        experiment_group="ADAPTIVE",
        consent_status="GRANTED",
        data_origin="REAL",
    )

    plan = classify_user(_account(), user, participation, STUDY)

    assert plan.enrollment_status == "SKIP_ALREADY_ENROLLED"
    assert plan.participant_code == "P000099"
    assert plan.consent_status == "GRANTED"


def test_classification_does_not_relabel_historical_activity():
    activity = SimpleNamespace(data_origin="UNKNOWN")

    classify_user(_account(), _user(), None, STUDY)

    assert activity.data_origin == "UNKNOWN"


def test_batch_validation_keeps_valid_row_when_another_row_is_inactive():
    plans = [
        classify_user(_account(row_number=2), _user(), None, STUDY),
        classify_user(
            _account(row_number=3, identifier="inactive@example.com"),
            _user(email="inactive@example.com", status=UserStatus.INACTIVE),
            None,
            STUDY,
        ),
    ]

    assert [plan.enrollment_status for plan in plans] == [
        "READY_TO_ENROLL",
        "INACTIVE",
    ]


def test_allowlist_reports_duplicate_identifier(tmp_path):
    path = tmp_path / "participants.csv"
    path.write_text(
        "identifier_type,identifier,allow_mentor\n"
        "email,REAL.USER@example.com,false\n"
        "email,real.user@example.com,false\n",
        encoding="utf-8",
    )

    accounts = read_allowlist(path)

    assert accounts[0].duplicate_input is False
    assert accounts[1].duplicate_input is True


class _Scalars:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class _Result:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return _Scalars(self.values)

    def scalar_one_or_none(self):
        return self.values[0] if self.values else None


@pytest.mark.asyncio
async def test_user_not_found_lookup():
    db = SimpleNamespace(execute=AsyncMock(return_value=_Result([])))

    user, status = await _lookup_user(db, _account())

    assert user is None
    assert status == "NOT_FOUND"


@pytest.mark.asyncio
async def test_repeated_service_enrollment_is_idempotent():
    user = _user()
    existing = ResearchParticipation(
        user_id=user.id,
        participant_code="P000101",
        study_code=STUDY,
        experiment_group="ADAPTIVE",
        consent_status="GRANTED",
        data_origin="REAL",
    )
    db = SimpleNamespace(
        get=AsyncMock(return_value=user),
        execute=AsyncMock(side_effect=[_Result([SimpleNamespace()]), _Result([existing])]),
        commit=AsyncMock(),
    )
    payload = ResearchEnrollmentRequest(
        user_id=user.id,
        study_code=STUDY,
        experiment_group="ADAPTIVE",
        consent_status="NOT_REQUESTED",
        data_origin="REAL",
    )

    result = await ResearchService().enroll(db, payload)

    assert result is existing
    assert result.participant_code == "P000101"
    assert result.consent_status == "GRANTED"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_service_enrolls_selected_real_user_without_granting_consent():
    user = _user()
    added = []
    db = SimpleNamespace(
        get=AsyncMock(return_value=user),
        execute=AsyncMock(side_effect=[_Result([SimpleNamespace()]), _Result([])]),
        add=added.append,
        flush=AsyncMock(),
        commit=AsyncMock(),
        refresh=AsyncMock(),
    )
    payload = ResearchEnrollmentRequest(
        user_id=user.id,
        study_code=STUDY,
        experiment_group="ADAPTIVE",
        consent_status="NOT_REQUESTED",
        data_origin="REAL",
    )

    result = await ResearchService().enroll(db, payload)

    assert result in added
    assert result.consent_status == "NOT_REQUESTED"
    assert result.experiment_group == "ADAPTIVE"
    assert result.data_origin == "REAL"
    db.commit.assert_awaited_once()
