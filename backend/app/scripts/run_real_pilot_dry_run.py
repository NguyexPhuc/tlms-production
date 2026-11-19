"""Run one idempotent TEST-origin research pilot through production services."""
from __future__ import annotations

import asyncio
import json
import secrets
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.certification import ExamAnswer, ExamResult
from app.models.development import (
    AdaptiveDecisionHistory,
    Question,
    QuestionAttemptHistory,
    ResearchConsentStatus,
    ResearchDataOrigin,
    ResearchExperimentGroup,
    ResearchParticipation,
    ResearchQuestionPhase,
    ResearchStudy,
    ResearchStudyQuestion,
    SkillMasteryHistory,
)
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest
from app.schemas.certification import AttemptAnswerSubmit
from app.schemas.research import ResearchEnrollmentRequest
from app.services.certification import certification_service
from app.services.local_auth import local_auth_service
from app.services.question import question_service
from app.services.research import research_service


STUDY_CODE = "TLMS_ADAPTIVE_REAL_PILOT_2026"
TEST_EMAIL = "research.dryrun.2026@example.com"


async def _ensure_test_user(db) -> tuple[User, bool]:
    user = await local_auth_service.get_user_by_email(db, TEST_EMAIL)
    if user is not None:
        return user, False
    user = await local_auth_service.register(
        db,
        RegisterRequest(
            email=TEST_EMAIL,
            password=secrets.token_urlsafe(24),
            phone="0000000000",
            firstName="Research",
            lastName="Dry Run",
        ),
    )
    await db.commit()
    await db.refresh(user)
    return user, True


async def _ensure_participation(db, user: User) -> ResearchParticipation:
    participation = (
        await db.execute(
            select(ResearchParticipation).where(ResearchParticipation.user_id == user.id)
        )
    ).scalar_one_or_none()
    if participation is None:
        participation = await research_service.enroll(
            db,
            ResearchEnrollmentRequest(
                user_id=user.id,
                study_code=STUDY_CODE,
                experiment_group=ResearchExperimentGroup.ADAPTIVE.value,
                consent_status=ResearchConsentStatus.PENDING.value,
                data_origin=ResearchDataOrigin.TEST.value,
            ),
        )
    if participation.study_code != STUDY_CODE:
        raise RuntimeError("Reserved dry-run account is assigned to another study")
    if participation.data_origin != ResearchDataOrigin.TEST.value:
        raise RuntimeError("Dry-run participation must have TEST data origin")
    if participation.experiment_group != ResearchExperimentGroup.ADAPTIVE.value:
        raise RuntimeError("Dry-run participation must use ADAPTIVE assignment")
    if participation.consent_status == ResearchConsentStatus.PENDING.value:
        participation = await research_service.update_my_consent(
            db, user.id, ResearchConsentStatus.GRANTED.value
        )
    if participation.consent_status != ResearchConsentStatus.GRANTED.value:
        raise RuntimeError("Dry-run participant has not granted consent")
    return participation


async def _review_pending_exam_answers(db, attempt_id, reviewer: User) -> None:
    pending = list(
        (
            await db.execute(
                select(ExamAnswer).where(
                    ExamAnswer.attempt_id == attempt_id,
                    ExamAnswer.score_awarded.is_(None),
                ).options(selectinload(ExamAnswer.exam_question))
            )
        ).scalars().all()
    )
    for answer in pending:
        await certification_service.review_answer(
            db,
            reviewer,
            answer.id,
            float(answer.exam_question.points),
            "TEST dry-run reference answer accepted.",
        )


async def _complete_exam(db, user: User, reviewer: User, exam_id) -> ExamResult:
    existing = (
        await db.execute(
            select(ExamResult).where(
                ExamResult.user_id == user.id,
                ExamResult.exam_id == exam_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    attempt = await certification_service.start_exam(db, user, exam_id)
    answer_payloads = []
    for item in attempt["questions"]:
        question = await db.get(Question, item["question_id"])
        if question.question_type == "multiple_choice":
            answer_payloads.append(
                AttemptAnswerSubmit(
                    exam_question_id=item["id"],
                    selected_options=[question.correct_option],
                )
            )
        else:
            answer_payloads.append(
                AttemptAnswerSubmit(
                    exam_question_id=item["id"],
                    text_answer=question.expected_answer or "Reference response",
                )
            )
    result = await certification_service.submit_exam(
        db, user, attempt["id"], answer_payloads
    )
    if result["status"] == "pending_review":
        await _review_pending_exam_answers(db, attempt["id"], reviewer)
    completed = (
        await db.execute(
            select(ExamResult).where(
                ExamResult.user_id == user.id,
                ExamResult.exam_id == exam_id,
            )
        )
    ).scalar_one_or_none()
    if completed is None:
        raise RuntimeError("Research assessment did not produce an ExamResult")
    return completed


async def _train_attempt_count(db, user_id) -> int:
    return int(
        (
            await db.execute(
                select(func.count(QuestionAttemptHistory.id))
                .join(
                    ResearchStudyQuestion,
                    ResearchStudyQuestion.question_id == QuestionAttemptHistory.question_id,
                )
                .where(
                    QuestionAttemptHistory.user_id == user_id,
                    QuestionAttemptHistory.data_origin == ResearchDataOrigin.TEST.value,
                    ResearchStudyQuestion.study_code == STUDY_CODE,
                    ResearchStudyQuestion.phase == ResearchQuestionPhase.TRAIN.value,
                )
            )
        ).scalar()
        or 0
    )


async def _complete_training(db, user: User, minimum: int = 20) -> int:
    count = await _train_attempt_count(db, user.id)
    while count < minimum:
        questions = await question_service.list_questions(db, user)
        if not questions:
            raise RuntimeError(f"Adaptive selector exhausted after {count} TRAIN attempts")
        for question in questions:
            if count >= minimum:
                break
            await asyncio.sleep(0.02)
            answer = (
                question.correct_option
                if question.question_type == "multiple_choice"
                else question.expected_answer or "Reference response"
            )
            await question_service.submit_answer(db, user, question.id, answer)
            count = await _train_attempt_count(db, user.id)
    return count


async def run() -> dict:
    async with AsyncSessionLocal() as db:
        study = await research_service.get_study(db, STUDY_CODE)
        if not study.pre_exam_id or not study.post_exam_id:
            raise RuntimeError("PRE and POST exams must be configured before dry-run")
        user, user_created = await _ensure_test_user(db)
        participation = await _ensure_participation(db, user)
        reviewer = (
            await db.execute(select(User).where(User.roles.any(UserRole.ADMIN.value)).limit(1))
        ).scalar_one_or_none()
        if reviewer is None:
            raise RuntimeError("An admin reviewer is required for research short answers")

        pre = await _complete_exam(db, user, reviewer, study.pre_exam_id)
        training_count = await _complete_training(db, user, minimum=20)
        post = await _complete_exam(db, user, reviewer, study.post_exam_id)
        if participation.completed_at is None:
            participation = await research_service.complete(db, participation.participant_code)

        attempts = list(
            (
                await db.execute(
                    select(QuestionAttemptHistory).where(
                        QuestionAttemptHistory.user_id == user.id,
                        QuestionAttemptHistory.data_origin == ResearchDataOrigin.TEST.value,
                    )
                )
            ).scalars().all()
        )
        mastery_count = int(
            (
                await db.execute(
                    select(func.count(SkillMasteryHistory.id)).where(
                        SkillMasteryHistory.user_id == user.id,
                        SkillMasteryHistory.data_origin == ResearchDataOrigin.TEST.value,
                    )
                )
            ).scalar()
            or 0
        )
        decision_count = int(
            (
                await db.execute(
                    select(func.count(AdaptiveDecisionHistory.id)).where(
                        AdaptiveDecisionHistory.user_id == user.id,
                        AdaptiveDecisionHistory.data_origin == ResearchDataOrigin.TEST.value,
                    )
                )
            ).scalar()
            or 0
        )
        return {
            "participant_code": participation.participant_code,
            "data_origin": participation.data_origin,
            "experiment_group": participation.experiment_group,
            "user_created": user_created,
            "consent": participation.consent_status,
            "pre_completed": pre is not None,
            "train_attempts": training_count,
            "post_completed": post is not None,
            "pilot_completed": participation.completed_at is not None,
            "question_attempt_history": len(attempts),
            "skill_mastery_history": mastery_count,
            "adaptive_decision_history": decision_count,
            "response_time": dict(Counter(item.response_time_status for item in attempts)),
        }


def main() -> None:
    print(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
