"""Restricted research study administration endpoints."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_mentor
from app.core.database import get_db
from app.models.user import User
from app.schemas.research import (
    FixedSequenceConfigure,
    FixedSequenceItemResponse,
    ResearchConsentUpdate,
    ResearchEnrollmentRequest,
    ResearchParticipantProgressResponse,
    ResearchParticipationResponse,
    ResearchStudyCreate,
    ResearchStudyResponse,
    ResearchStudyUpdate,
    ResearchSurveyResponse,
    ResearchSurveySubmit,
)
from app.services.research import is_active_research_participant, research_service


router = APIRouter(prefix="/research", tags=["Research Pilot"])


def _participant_response(participation) -> ResearchParticipationResponse:
    return ResearchParticipationResponse(
        **{
            field: getattr(participation, field)
            for field in ResearchParticipationResponse.model_fields
            if field != "active_for_research"
        },
        active_for_research=is_active_research_participant(participation),
    )


@router.get("/me", response_model=ResearchParticipantProgressResponse)
async def get_my_research_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await research_service.participant_progress(db, current_user.id)


@router.post("/my-survey", response_model=ResearchSurveyResponse)
async def submit_my_research_survey(
    payload: ResearchSurveySubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await research_service.submit_survey(db, current_user.id, payload)


@router.post("/studies", response_model=ResearchStudyResponse, status_code=status.HTTP_201_CREATED)
async def create_study(
    payload: ResearchStudyCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_mentor),
):
    return await research_service.create_study(db, payload)


@router.patch("/studies/{study_code}", response_model=ResearchStudyResponse)
async def update_study(
    study_code: str,
    payload: ResearchStudyUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_mentor),
):
    return await research_service.update_study(db, study_code, payload)


@router.post(
    "/studies/{study_code}/fixed-sequence",
    response_model=list[FixedSequenceItemResponse],
    status_code=status.HTTP_201_CREATED,
)
async def configure_fixed_sequence(
    study_code: str,
    payload: FixedSequenceConfigure,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_mentor),
):
    return await research_service.configure_fixed_sequence(db, study_code, payload)


@router.post(
    "/participants",
    response_model=ResearchParticipationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def enroll_participant(
    payload: ResearchEnrollmentRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_mentor),
):
    return _participant_response(await research_service.enroll(db, payload))


@router.patch("/participants/{participant_code}/consent", response_model=ResearchParticipationResponse)
async def update_participant_consent(
    participant_code: str,
    payload: ResearchConsentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_mentor),
):
    participation = await research_service.update_consent(db, participant_code, payload.consent_status)
    return _participant_response(participation)


@router.patch("/my-consent", response_model=ResearchParticipationResponse)
async def update_my_consent(
    payload: ResearchConsentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    participation = await research_service.update_my_consent(
        db,
        current_user.id,
        payload.consent_status,
    )
    return _participant_response(participation)


@router.post("/participants/{participant_code}/complete", response_model=ResearchParticipationResponse)
async def complete_participant(
    participant_code: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_mentor),
):
    return _participant_response(await research_service.complete(db, participant_code))

