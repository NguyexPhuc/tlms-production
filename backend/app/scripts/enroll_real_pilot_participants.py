"""Safely enroll an explicit allowlist of REAL research participants."""
from __future__ import annotations

import argparse
import asyncio
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.development import (
    QuestionAttemptHistory,
    ResearchConsentStatus,
    ResearchDataOrigin,
    ResearchExperimentGroup,
    ResearchParticipation,
    ResearchQuestionPhase,
    ResearchStudy,
    ResearchStudyQuestion,
    ResearchStudyStatus,
)
from app.models.user import User, UserRole, UserStatus
from app.schemas.research import ResearchEnrollmentRequest
from app.services.research import research_service


DEFAULT_STUDY_CODE = "TLMS_ADAPTIVE_REAL_PILOT_2026"
REPORT_COLUMNS = [
    "input_identifier_type",
    "input_identifier_masked",
    "lookup_status",
    "participant_code",
    "enrollment_status",
    "consent_status",
    "experiment_group",
    "data_origin",
    "message",
]
SUPPORTED_IDENTIFIER_TYPES = {"email", "student_id", "user_id"}
LEARNER_ROLES = {UserRole.CANDIDATE.value, UserRole.MEMBER.value}
BLOCKED_ROLES = {UserRole.ADMIN.value, "system", "service", "test"}
NON_REAL_ORIGINS = {
    ResearchDataOrigin.TEST.value,
    ResearchDataOrigin.DEMO.value,
    ResearchDataOrigin.SEED.value,
    ResearchDataOrigin.SYNTHETIC.value,
}


def _value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _truthy(value: str) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "y"}


def mask_identifier(identifier_type: str, identifier: str) -> str:
    value = identifier.strip()
    if identifier_type == "email" and "@" in value:
        local, domain = value.split("@", 1)
        visible = local[:2] if len(local) > 1 else local[:1]
        return f"{visible}***@{domain}"
    if identifier_type == "student_id":
        return "*" * max(0, len(value) - 3) + value[-3:]
    if identifier_type == "user_id":
        return value[:8] + "..." if len(value) > 8 else "***"
    return "***"


@dataclass
class InputAccount:
    row_number: int
    identifier_type: str
    identifier: str
    allow_mentor: bool = False
    duplicate_input: bool = False


@dataclass
class EnrollmentPlan:
    account: InputAccount
    user_id: Optional[UUID]
    lookup_status: str
    enrollment_status: str
    message: str
    participant_code: str = ""
    consent_status: str = ""
    experiment_group: str = ""
    data_origin: str = ""

    def report_row(self) -> dict[str, str]:
        return {
            "input_identifier_type": self.account.identifier_type,
            "input_identifier_masked": mask_identifier(
                self.account.identifier_type, self.account.identifier
            ),
            "lookup_status": self.lookup_status,
            "participant_code": self.participant_code,
            "enrollment_status": self.enrollment_status,
            "consent_status": self.consent_status,
            "experiment_group": self.experiment_group,
            "data_origin": self.data_origin,
            "message": self.message,
        }


def read_allowlist(path: Path) -> list[InputAccount]:
    if not path.is_file():
        raise ValueError(f"Allowlist file not found: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"identifier_type", "identifier"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("CSV requires identifier_type and identifier columns")
        accounts: list[InputAccount] = []
        seen: set[tuple[str, str]] = set()
        for row_number, row in enumerate(reader, start=2):
            identifier_type = str(row.get("identifier_type") or "").strip().casefold()
            identifier = str(row.get("identifier") or "").strip()
            if identifier_type == "email":
                identifier = identifier.casefold()
            key = (identifier_type, identifier)
            duplicate = bool(identifier) and key in seen
            if identifier:
                seen.add(key)
            accounts.append(
                InputAccount(
                    row_number=row_number,
                    identifier_type=identifier_type,
                    identifier=identifier,
                    allow_mentor=_truthy(row.get("allow_mentor") or ""),
                    duplicate_input=duplicate,
                )
            )
    return accounts


def has_test_or_demo_evidence(
    user: User,
    participation: Optional[ResearchParticipation],
) -> bool:
    if participation and _value(participation.data_origin) in NON_REAL_ORIGINS:
        return True
    email = (user.email or "").strip().casefold()
    local, _, domain = email.partition("@")
    identity = (user.s4h_user_id or "").strip().casefold()
    prefixes = ("test-", "test.", "demo-", "demo.", "seed-", "seed.")
    return domain == "tlms.local" or local.startswith(prefixes) or identity.startswith(prefixes)


def classify_user(
    account: InputAccount,
    user: User,
    participation: Optional[ResearchParticipation],
    study_code: str,
) -> EnrollmentPlan:
    if has_test_or_demo_evidence(user, participation):
        return EnrollmentPlan(
            account, user.id, "FOUND", "TEST_OR_DEMO",
            "Account has explicit TEST/DEMO/SEED evidence and was skipped.",
        )
    if _value(user.status) != UserStatus.ACTIVE.value:
        return EnrollmentPlan(
            account, user.id, "FOUND", "INACTIVE", "Account is not active."
        )
    roles = {str(role).strip().casefold() for role in (user.roles or [])}
    if roles & BLOCKED_ROLES:
        return EnrollmentPlan(
            account, user.id, "FOUND", "INELIGIBLE_ROLE",
            "Admin/system/service/test roles are not eligible.",
        )
    if UserRole.MENTOR.value in roles and not account.allow_mentor:
        return EnrollmentPlan(
            account, user.id, "FOUND", "INELIGIBLE_ROLE",
            "Mentor enrollment requires allow_mentor=true on this CSV row.",
        )
    if not (roles & LEARNER_ROLES or UserRole.MENTOR.value in roles):
        return EnrollmentPlan(
            account, user.id, "FOUND", "INELIGIBLE_ROLE",
            "Account does not have an eligible candidate/member/mentor role.",
        )
    if participation is not None:
        if participation.study_code == study_code:
            return EnrollmentPlan(
                account, user.id, "FOUND", "SKIP_ALREADY_ENROLLED",
                "Account is already enrolled; no fields were changed.",
                participant_code=participation.participant_code,
                consent_status=_value(participation.consent_status),
                experiment_group=_value(participation.experiment_group),
                data_origin=_value(participation.data_origin),
            )
        return EnrollmentPlan(
            account, user.id, "FOUND", "SKIP_REVIEW_REQUIRED",
            "Account already has a participation record for another study.",
            participant_code=participation.participant_code,
            consent_status=_value(participation.consent_status),
            experiment_group=_value(participation.experiment_group),
            data_origin=_value(participation.data_origin),
        )
    return EnrollmentPlan(
        account, user.id, "FOUND", "READY_TO_ENROLL",
        "Eligible for explicit REAL enrollment with consent NOT_REQUESTED.",
        consent_status=ResearchConsentStatus.NOT_REQUESTED.value,
        experiment_group=ResearchExperimentGroup.ADAPTIVE.value,
        data_origin=ResearchDataOrigin.REAL.value,
    )


async def _lookup_user(db, account: InputAccount) -> tuple[Optional[User], str]:
    if account.identifier_type not in SUPPORTED_IDENTIFIER_TYPES:
        return None, "INVALID_IDENTIFIER_TYPE"
    if not account.identifier:
        return None, "INVALID_IDENTIFIER"
    if account.identifier_type == "email":
        users = list((await db.execute(
            select(User).where(func.lower(User.email) == account.identifier.casefold())
        )).scalars().all())
    elif account.identifier_type == "student_id":
        users = list((await db.execute(
            select(User).where(User.student_id == account.identifier)
        )).scalars().all())
    else:
        try:
            user_id = UUID(account.identifier)
        except ValueError:
            return None, "INVALID_IDENTIFIER"
        users = list((await db.execute(
            select(User).where(User.id == user_id)
        )).scalars().all())
    if not users:
        return None, "NOT_FOUND"
    if len(users) > 1:
        return None, "SKIP_REVIEW_REQUIRED"
    return users[0], "FOUND"


async def build_plan(accounts: list[InputAccount], study_code: str) -> tuple[list[EnrollmentPlan], int]:
    plans: list[EnrollmentPlan] = []
    resolved_user_ids: set[UUID] = set()
    async with AsyncSessionLocal() as db:
        study = (await db.execute(
            select(ResearchStudy).where(ResearchStudy.study_code == study_code)
        )).scalar_one_or_none()
        if study is None:
            raise ValueError(f"Study not found: {study_code}")
        if study.study_status not in {
            ResearchStudyStatus.PILOT.value,
            ResearchStudyStatus.ACTIVE.value,
        }:
            raise ValueError(f"Study is not open for enrollment: {study.study_status}")
        real_before = int((await db.execute(
            select(func.count(ResearchParticipation.id)).where(
                ResearchParticipation.study_code == study_code,
                ResearchParticipation.data_origin == ResearchDataOrigin.REAL.value,
            )
        )).scalar() or 0)
        for account in accounts:
            if account.duplicate_input:
                plans.append(EnrollmentPlan(
                    account, None, "DUPLICATE_IDENTIFIER", "SKIP_DUPLICATE_INPUT",
                    "Duplicate identifier in the input CSV.",
                ))
                continue
            user, lookup_status = await _lookup_user(db, account)
            if user is None:
                message = {
                    "NOT_FOUND": "No matching account was found.",
                    "SKIP_REVIEW_REQUIRED": "Lookup matched multiple accounts.",
                }.get(lookup_status, "Identifier is invalid or unsupported.")
                plans.append(EnrollmentPlan(
                    account, None, lookup_status, lookup_status, message
                ))
                continue
            if user.id in resolved_user_ids:
                plans.append(EnrollmentPlan(
                    account, user.id, "FOUND", "SKIP_DUPLICATE_USER",
                    "Another input row already resolves to this account.",
                ))
                continue
            resolved_user_ids.add(user.id)
            participation = (await db.execute(
                select(ResearchParticipation).where(
                    ResearchParticipation.user_id == user.id
                )
            )).scalar_one_or_none()
            plans.append(classify_user(account, user, participation, study_code))
        await db.rollback()
    return plans, real_before


async def apply_plan(plans: list[EnrollmentPlan], study_code: str) -> None:
    for plan in plans:
        if plan.enrollment_status != "READY_TO_ENROLL" or plan.user_id is None:
            continue
        async with AsyncSessionLocal() as db:
            try:
                user = await db.get(User, plan.user_id)
                participation = (await db.execute(
                    select(ResearchParticipation).where(
                        ResearchParticipation.user_id == plan.user_id
                    )
                )).scalar_one_or_none()
                if user is None:
                    plan.lookup_status = "NOT_FOUND"
                    plan.enrollment_status = "NOT_FOUND"
                    plan.message = "Account disappeared before apply."
                    continue
                current = classify_user(plan.account, user, participation, study_code)
                if current.enrollment_status != "READY_TO_ENROLL":
                    plan.lookup_status = current.lookup_status
                    plan.enrollment_status = current.enrollment_status
                    plan.message = current.message
                    plan.participant_code = current.participant_code
                    plan.consent_status = current.consent_status
                    plan.experiment_group = current.experiment_group
                    plan.data_origin = current.data_origin
                    continue
                enrolled = await research_service.enroll(
                    db,
                    ResearchEnrollmentRequest(
                        user_id=user.id,
                        study_code=study_code,
                        experiment_group=ResearchExperimentGroup.ADAPTIVE.value,
                        consent_status=ResearchConsentStatus.NOT_REQUESTED.value,
                        data_origin=ResearchDataOrigin.REAL.value,
                    ),
                )
                plan.participant_code = enrolled.participant_code
                plan.enrollment_status = "ENROLLED"
                plan.consent_status = _value(enrolled.consent_status)
                plan.experiment_group = _value(enrolled.experiment_group)
                plan.data_origin = _value(enrolled.data_origin)
                plan.message = "REAL participant enrolled; consent was not granted."
            except Exception as exc:
                await db.rollback()
                plan.enrollment_status = "ERROR"
                plan.message = f"Enrollment failed: {type(exc).__name__}"


async def research_totals(study_code: str) -> dict[str, int]:
    async with AsyncSessionLocal() as db:
        real_filter = (
            ResearchParticipation.study_code == study_code,
            ResearchParticipation.data_origin == ResearchDataOrigin.REAL.value,
        )
        total = int((await db.execute(
            select(func.count(ResearchParticipation.id)).where(*real_filter)
        )).scalar() or 0)
        not_requested = int((await db.execute(
            select(func.count(ResearchParticipation.id)).where(
                *real_filter,
                ResearchParticipation.consent_status == ResearchConsentStatus.NOT_REQUESTED.value,
            )
        )).scalar() or 0)
        granted = int((await db.execute(
            select(func.count(ResearchParticipation.id)).where(
                *real_filter,
                ResearchParticipation.consent_status == ResearchConsentStatus.GRANTED.value,
            )
        )).scalar() or 0)
        observations = int((await db.execute(
            select(func.count(QuestionAttemptHistory.id))
            .join(
                ResearchParticipation,
                ResearchParticipation.user_id == QuestionAttemptHistory.user_id,
            )
            .join(
                ResearchStudyQuestion,
                ResearchStudyQuestion.question_id == QuestionAttemptHistory.question_id,
            )
            .where(
                ResearchParticipation.study_code == study_code,
                ResearchParticipation.data_origin == ResearchDataOrigin.REAL.value,
                ResearchParticipation.consent_status == ResearchConsentStatus.GRANTED.value,
                ResearchStudyQuestion.study_code == study_code,
                ResearchStudyQuestion.phase == ResearchQuestionPhase.TRAIN.value,
                QuestionAttemptHistory.data_origin == ResearchDataOrigin.REAL.value,
                QuestionAttemptHistory.submitted_at >= ResearchParticipation.consent_granted_at,
            )
        )).scalar() or 0)
        await db.rollback()
    return {
        "real_total": total,
        "not_requested": not_requested,
        "granted": granted,
        "observations": observations,
    }


def write_report(path: Path, plans: list[EnrollmentPlan]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(plan.report_row() for plan in plans)


def print_summary(
    study_code: str,
    plans: list[EnrollmentPlan],
    real_before: int,
    totals: dict[str, int],
) -> None:
    statuses = Counter(plan.enrollment_status for plan in plans)
    found = sum(plan.lookup_status == "FOUND" for plan in plans)
    skipped = sum(
        status not in {"READY_TO_ENROLL", "ENROLLED", "SKIP_ALREADY_ENROLLED", "NOT_FOUND", "ERROR"}
        for status in (plan.enrollment_status for plan in plans)
    )
    print(f"Study:\n{study_code}\n")
    print(f"Input accounts: {len(plans)}")
    print(f"Found: {found}")
    print(f"Ready: {statuses['READY_TO_ENROLL']}")
    print(f"Enrolled: {statuses['ENROLLED']}")
    print(f"Already enrolled: {statuses['SKIP_ALREADY_ENROLLED']}")
    print(f"Not found: {statuses['NOT_FOUND']}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {statuses['ERROR']}")
    print(f"REAL participants before: {real_before}")
    print(f"REAL participants total: {totals['real_total']}")
    print(f"Consent NOT_REQUESTED: {totals['not_requested']}")
    print(f"Consent GRANTED: {totals['granted']}")
    print(f"REAL observations: {totals['observations']}")


async def run(args) -> None:
    accounts = read_allowlist(args.input)
    plans, real_before = await build_plan(accounts, args.study_code)
    if args.apply:
        await apply_plan(plans, args.study_code)
    write_report(args.output, plans)
    totals = await research_totals(args.study_code)
    print_summary(args.study_code, plans, real_before, totals)
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Report: {args.output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--study-code", default=DEFAULT_STUDY_CODE)
    parser.add_argument("--output", type=Path, default=Path("/tmp/enrollment_report.csv"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
