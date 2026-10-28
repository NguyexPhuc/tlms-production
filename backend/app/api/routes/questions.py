"""Question routes."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_mentor
from app.core.database import get_db
from app.models.user import MemberLevel, User
from app.schemas.question import (
    QuestionAnswerResponse,
    QuestionAnswerReview,
    QuestionAnswerSubmit,
    QuestionCreate,
    QuestionListResponse,
    QuestionResponse,
    QuestionUpdate,
)
from app.services.question import question_service

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.post(
    "",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_mentor)],
)
async def create_question(
    question_data: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await question_service.create_question(db, current_user, question_data)


@router.get("", response_model=QuestionListResponse)
async def list_questions(
    target_member_level: Optional[MemberLevel] = Query(None),
    include_archived: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    questions = await question_service.list_questions(
        db,
        current_user,
        target_member_level=target_member_level.value if target_member_level else None,
        include_archived=include_archived,
    )
    return QuestionListResponse(questions=questions, total=len(questions))


@router.patch(
    "/{question_id:uuid}",
    response_model=QuestionResponse,
    dependencies=[Depends(require_mentor)],
)
async def update_question(
    question_id: UUID,
    question_data: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await question_service.update_question(db, current_user, question_id, question_data)


@router.post("/{question_id:uuid}/answer", response_model=QuestionAnswerResponse)
async def submit_question_answer(
    question_id: UUID,
    answer_data: QuestionAnswerSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await question_service.submit_answer(db, current_user, question_id, answer_data.answer)


@router.get("/answers", response_model=list[QuestionAnswerResponse])
async def list_question_answers(
    pending_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await question_service.list_answers(db, current_user, pending_only=pending_only)


@router.post(
    "/answers/{answer_id}/review",
    response_model=QuestionAnswerResponse,
    dependencies=[Depends(require_mentor)],
)
async def review_question_answer(
    answer_id: UUID,
    review_data: QuestionAnswerReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await question_service.review_answer(
        db,
        current_user,
        answer_id,
        review_data.status,
        review_data.manager_score,
        review_data.final_score,
        review_data.feedback,
    )
