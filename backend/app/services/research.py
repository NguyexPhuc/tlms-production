"""Research study configuration and explicit participant lifecycle."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.certification import AssessmentPurpose, Exam, ExamResult
from app.models.development import (
    QuestionAttemptHistory,
    Question,
    ResearchConsentStatus,
    ResearchDataOrigin,
    ResearchFixedQuestionSequence,
    ResearchParticipation,
    ResearchQuestionPhase,
    ResearchStudy,
    ResearchStudyQuestion,
    ResearchSurveyResponse,
)
from app.models.user import User
from app.schemas.research import (
    FixedSequenceConfigure,
    ResearchEnrollmentRequest,
    ResearchStudyCreate,
    ResearchStudyUpdate,
    ResearchSurveySubmit,
)


def is_active_research_participant(participation: ResearchParticipation) -> bool:
    """Consent is explicit; a REAL record is never activated implicitly."""
    return (
        participation.study_code is not None
        and participation.consent_status == ResearchConsentStatus.GRANTED.value
        and participation.data_origin in {
            ResearchDataOrigin.REAL.value,
            ResearchDataOrigin.DEMO.value,
            ResearchDataOrigin.TEST.value,
            ResearchDataOrigin.SEED.value,
        }
        and participation.completed_at is None
    )


class ResearchService:
    async def participant_progress(self, db: AsyncSession, user_id: UUID) -> dict:
        participation = await self.get_participation_by_user(db, user_id)
        if not participation.study_code:
            raise NotFoundException("Research participant is not assigned to a study")
        study = await self.get_study(db, participation.study_code)
        pre_completed, train_completed, post_completed = await self._completion_progress(
            db,
            participation,
            study,
        )
        survey_completed = (
            await db.execute(
                select(ResearchSurveyResponse.id).where(
                    ResearchSurveyResponse.participation_id == participation.id
                )
            )
        ).scalar_one_or_none() is not None
        return {
            "study_code": study.study_code,
            "study_name": study.name,
            "participant_code": participation.participant_code,
            "experiment_group": participation.experiment_group,
            "consent_status": participation.consent_status,
            "data_origin": participation.data_origin,
            "pre_exam_id": study.pre_exam_id,
            "post_exam_id": study.post_exam_id,
            "pre_completed": pre_completed,
            "train_completed": train_completed,
            "train_required": 20,
            "post_completed": post_completed,
            "survey_completed": survey_completed,
            "completed_at": participation.completed_at,
        }

    async def submit_survey(
        self,
        db: AsyncSession,
        user_id: UUID,
        payload: ResearchSurveySubmit,
    ) -> ResearchSurveyResponse:
        participation = await self.get_participation_by_user(db, user_id, lock=True)
        if participation.consent_status != ResearchConsentStatus.GRANTED.value:
            raise BadRequestException("Granted consent is required before the survey")
        if not participation.study_code:
            raise BadRequestException("Participant is not assigned to a research study")
        existing = (
            await db.execute(
                select(ResearchSurveyResponse).where(
                    ResearchSurveyResponse.participation_id == participation.id
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        study = await self.get_study(db, participation.study_code)
        pre_completed, train_completed, post_completed = await self._completion_progress(
            db,
            participation,
            study,
        )
        missing = []
        if not pre_completed:
            missing.append("PRE")
        if train_completed < 20:
            missing.append(f"TRAIN {train_completed}/20")
        if not post_completed:
            missing.append("POST")
        if missing:
            raise BadRequestException("Complete the pilot before the survey: " + ", ".join(missing))
        survey = ResearchSurveyResponse(
            participation_id=participation.id,
            study_code=participation.study_code,
            likert_answers=payload.likert_answers,
            useful_feedback=(payload.useful_feedback or "").strip() or None,
            improvement_feedback=(payload.improvement_feedback or "").strip() or None,
        )
        db.add(survey)
        participation.completed_at = participation.completed_at or datetime.utcnow()
        await db.commit()
        await db.refresh(survey)
        return survey

    async def _completion_progress(
        self,
        db: AsyncSession,
        participation: ResearchParticipation,
        study: ResearchStudy,
    ) -> tuple[bool, int, bool]:
        exam_ids = [item for item in (study.pre_exam_id, study.post_exam_id) if item]
        result_exam_ids = set()
        if exam_ids:
            result_exam_ids = set(
                (
                    await db.execute(
                        select(ExamResult.exam_id).where(
                            ExamResult.user_id == participation.user_id,
                            ExamResult.exam_id.in_(exam_ids),
                        )
                    )
                ).scalars().all()
            )
        train_query = (
            select(func.count(QuestionAttemptHistory.id))
            .join(
                ResearchStudyQuestion,
                ResearchStudyQuestion.question_id == QuestionAttemptHistory.question_id,
            )
            .where(
                QuestionAttemptHistory.user_id == participation.user_id,
                ResearchStudyQuestion.study_code == participation.study_code,
                ResearchStudyQuestion.phase == ResearchQuestionPhase.TRAIN.value,
                QuestionAttemptHistory.data_origin == participation.data_origin,
            )
        )
        start_at = participation.consent_granted_at or participation.enrolled_at
        if start_at is not None:
            train_query = train_query.where(QuestionAttemptHistory.submitted_at >= start_at)
        train_completed = int((await db.execute(train_query)).scalar() or 0)
        return (
            bool(study.pre_exam_id and study.pre_exam_id in result_exam_ids),
            train_completed,
            bool(study.post_exam_id and study.post_exam_id in result_exam_ids),
        )

    async def get_study(self, db: AsyncSession, study_code: str) -> ResearchStudy:
        study = (
            await db.execute(select(ResearchStudy).where(ResearchStudy.study_code == study_code))
        ).scalar_one_or_none()
        if study is None:
            raise NotFoundException("Research study not found")
        return study

    async def create_study(self, db: AsyncSession, payload: ResearchStudyCreate) -> ResearchStudy:
        existing = (
            await db.execute(select(ResearchStudy.id).where(ResearchStudy.study_code == payload.study_code))
        ).scalar_one_or_none()
        if existing:
            raise BadRequestException("Research study code already exists")
        study = ResearchStudy(**payload.model_dump())
        db.add(study)
        await db.commit()
        await db.refresh(study)
        return study

    async def update_study(
        self,
        db: AsyncSession,
        study_code: str,
        payload: ResearchStudyUpdate,
    ) -> ResearchStudy:
        study = await self.get_study(db, study_code)
        values = payload.model_dump(exclude_unset=True)
        for field, purpose in (
            ("pre_exam_id", AssessmentPurpose.RESEARCH_PRE.value),
            ("post_exam_id", AssessmentPurpose.RESEARCH_POST.value),
        ):
            exam_id = values.get(field)
            if exam_id is None and field in values:
                continue
            if exam_id is not None:
                exam = await db.get(Exam, exam_id)
                if exam is None:
                    raise NotFoundException(f"{field} exam not found")
                if exam.assessment_purpose != purpose:
                    raise BadRequestException(f"{field} must reference an exam with purpose {purpose}")
        resulting_pre = values.get("pre_exam_id", study.pre_exam_id)
        resulting_post = values.get("post_exam_id", study.post_exam_id)
        if resulting_pre and resulting_pre == resulting_post:
            raise BadRequestException("PRE and POST assessments must be different exams")
        for field, value in values.items():
            setattr(study, field, value)
        await db.commit()
        await db.refresh(study)
        return study

    async def configure_fixed_sequence(
        self,
        db: AsyncSession,
        study_code: str,
        payload: FixedSequenceConfigure,
    ) -> list[ResearchFixedQuestionSequence]:
        study = await self.get_study(db, study_code)
        existing = (
            await db.execute(
                select(ResearchFixedQuestionSequence.id).where(
                    ResearchFixedQuestionSequence.study_code == study_code,
                    ResearchFixedQuestionSequence.sequence_version == payload.sequence_version,
                )
            )
        ).first()
        if existing:
            raise BadRequestException("This fixed sequence version already exists and is immutable")
        found_ids = set(
            (
                await db.execute(select(Question.id).where(Question.id.in_(payload.question_ids)))
            ).scalars().all()
        )
        missing = [str(item) for item in payload.question_ids if item not in found_ids]
        if missing:
            raise BadRequestException(f"Fixed sequence contains unknown questions: {', '.join(missing)}")
        items = [
            ResearchFixedQuestionSequence(
                study_code=study_code,
                sequence_version=payload.sequence_version,
                position=position,
                question_id=question_id,
                active=True,
            )
            for position, question_id in enumerate(payload.question_ids, start=1)
        ]
        db.add_all(items)
        study.fixed_sequence_version = payload.sequence_version
        await db.commit()
        for item in items:
            await db.refresh(item)
        return items

    async def enroll(
        self,
        db: AsyncSession,
        payload: ResearchEnrollmentRequest,
    ) -> ResearchParticipation:
        if await db.get(User, payload.user_id) is None:
            raise NotFoundException("User not found")
        await self.get_study(db, payload.study_code)
        participation = (
            await db.execute(
                select(ResearchParticipation)
                .where(ResearchParticipation.user_id == payload.user_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if participation and participation.study_code not in {None, payload.study_code}:
            raise BadRequestException("User is already assigned to another research study")
        if participation and participation.study_code == payload.study_code:
            # Enrollment is idempotent. Never reset consent, group, origin,
            # participant code, completion, or progress on a repeated request.
            return participation
        if participation is None:
            participation = ResearchParticipation(user_id=payload.user_id)
            db.add(participation)
            await db.flush()
        participation.study_code = payload.study_code
        participation.experiment_group = payload.experiment_group
        participation.consent_status = payload.consent_status
        participation.data_origin = payload.data_origin
        participation.enrolled_at = participation.enrolled_at or datetime.utcnow()
        participation.completed_at = None
        await db.commit()
        await db.refresh(participation)
        return participation

    async def update_consent(
        self,
        db: AsyncSession,
        participant_code: str,
        consent_status: str,
    ) -> ResearchParticipation:
        participation = await self.get_participation(db, participant_code, lock=True)
        self._validate_consent_transition(participation.consent_status, consent_status)
        participation.consent_status = consent_status
        if consent_status == ResearchConsentStatus.GRANTED.value and participation.consent_granted_at is None:
            participation.consent_granted_at = datetime.utcnow()
        await db.commit()
        await db.refresh(participation)
        return participation

    async def update_my_consent(
        self,
        db: AsyncSession,
        user_id: UUID,
        consent_status: str,
    ) -> ResearchParticipation:
        participation = await self.get_participation_by_user(db, user_id, lock=True)
        self._validate_consent_transition(participation.consent_status, consent_status)
        participation.consent_status = consent_status
        if consent_status == ResearchConsentStatus.GRANTED.value and participation.consent_granted_at is None:
            participation.consent_granted_at = datetime.utcnow()
        await db.commit()
        await db.refresh(participation)
        return participation

    @staticmethod
    def _validate_consent_transition(current: str, requested: str) -> None:
        allowed = {
            ResearchConsentStatus.NOT_REQUESTED.value: {
                ResearchConsentStatus.PENDING.value,
                ResearchConsentStatus.GRANTED.value,
                ResearchConsentStatus.DECLINED.value,
            },
            ResearchConsentStatus.PENDING.value: {
                ResearchConsentStatus.GRANTED.value,
                ResearchConsentStatus.DECLINED.value,
            },
            ResearchConsentStatus.GRANTED.value: {
                ResearchConsentStatus.WITHDRAWN.value,
            },
            ResearchConsentStatus.DECLINED.value: set(),
            ResearchConsentStatus.WITHDRAWN.value: set(),
        }
        if requested == current:
            return
        if requested not in allowed.get(current, set()):
            raise BadRequestException(f"Invalid consent transition: {current} -> {requested}")

    async def complete(
        self,
        db: AsyncSession,
        participant_code: str,
    ) -> ResearchParticipation:
        participation = await self.get_participation(db, participant_code, lock=True)
        if participation.consent_status != ResearchConsentStatus.GRANTED.value:
            raise BadRequestException("Granted consent is required before pilot completion")
        if not participation.study_code:
            raise BadRequestException("Participant is not assigned to a research study")
        study = await self.get_study(db, participation.study_code)
        if study.pre_exam_id is None or study.post_exam_id is None:
            raise BadRequestException("PRE and POST assessments must be configured")
        result_exam_ids = set(
            (
                await db.execute(
                    select(ExamResult.exam_id).where(
                        ExamResult.user_id == participation.user_id,
                        ExamResult.exam_id.in_([study.pre_exam_id, study.post_exam_id]),
                    )
                )
            ).scalars().all()
        )
        missing = []
        if study.pre_exam_id not in result_exam_ids:
            missing.append("PRE")
        start_at = participation.consent_granted_at or participation.enrolled_at
        train_query = (
            select(func.count(QuestionAttemptHistory.id))
            .join(
                ResearchStudyQuestion,
                ResearchStudyQuestion.question_id == QuestionAttemptHistory.question_id,
            )
            .where(
                QuestionAttemptHistory.user_id == participation.user_id,
                ResearchStudyQuestion.study_code == participation.study_code,
                ResearchStudyQuestion.phase == ResearchQuestionPhase.TRAIN.value,
                QuestionAttemptHistory.data_origin == participation.data_origin,
            )
        )
        if start_at is not None:
            train_query = train_query.where(QuestionAttemptHistory.submitted_at >= start_at)
        train_attempts = int((await db.execute(train_query)).scalar() or 0)
        if train_attempts < 20:
            missing.append(f"TRAIN {train_attempts}/20")
        if study.post_exam_id not in result_exam_ids:
            missing.append("POST")
        if missing:
            raise BadRequestException("Pilot is incomplete: " + ", ".join(missing))
        if participation.completed_at is None:
            participation.completed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(participation)
        return participation

    async def get_participation_by_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        *,
        lock: bool = False,
    ) -> ResearchParticipation:
        query = select(ResearchParticipation).where(ResearchParticipation.user_id == user_id)
        if lock:
            query = query.with_for_update()
        participation = (await db.execute(query)).scalar_one_or_none()
        if participation is None:
            raise NotFoundException("Research participant not found")
        return participation

    async def get_participation(
        self,
        db: AsyncSession,
        participant_code: str,
        *,
        lock: bool = False,
    ) -> ResearchParticipation:
        query = select(ResearchParticipation).where(
            ResearchParticipation.participant_code == participant_code
        )
        if lock:
            query = query.with_for_update()
        participation = (await db.execute(query)).scalar_one_or_none()
        if participation is None:
            raise NotFoundException("Research participant not found")
        return participation


research_service = ResearchService()

