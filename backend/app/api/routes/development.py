"""Member development routes."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_mentor
from app.core.exceptions import ForbiddenException
from app.core.database import get_db
from app.models.development import PromotionReview, PromotionStatus
from app.models.user import User
from app.schemas.development import (
    AchievementDashboard,
    DailyTaskAssignRequest,
    DailyTaskAssignResponse,
    DailyTaskReconcileRequest,
    DailyTaskReconcileResponse,
    ManagerDevelopmentSummary,
    MemberRoadmapResponse,
    MemberDevelopmentDashboard,
    MemberEvaluationResponse,
    PromotionDecisionRequest,
    PromotionReviewResponse,
)
from app.schemas.task import UserTaskProgressUpdate, UserTaskResponse
from app.services.achievement import achievement_service
from app.services.development import development_service

router = APIRouter(prefix="/development", tags=["Member Development"])


def promotion_to_response(review: PromotionReview) -> PromotionReviewResponse:
    return PromotionReviewResponse(
        id=review.id,
        user_id=review.user_id,
        user_email=review.user.email if review.user else None,
        user_full_name=review.user.full_name if review.user else None,
        from_member_level=review.from_member_level,
        to_member_level=review.to_member_level,
        status=review.status,
        metrics=review.metrics,
        manager_id=review.manager_id,
        manager_notes=review.manager_notes,
        decided_at=review.decided_at,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


@router.get("/me", response_model=MemberDevelopmentDashboard)
async def get_my_development_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await development_service.get_member_dashboard(db, current_user)


@router.get("/roadmap/me", response_model=MemberRoadmapResponse)
async def get_my_roadmap(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = await development_service.ensure_member_roadmap(db, current_user)
    if roadmap is None:
        raise ForbiddenException("Roadmap chỉ áp dụng cho candidate/member")
    return roadmap


@router.get("/achievements/me", response_model=AchievementDashboard)
async def get_my_achievements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await achievement_service.get_dashboard(db, current_user)


@router.post(
    "/tasks/{user_task_id:uuid}/progress",
    response_model=UserTaskResponse,
)
async def update_my_task_progress(
    user_task_id: UUID,
    progress_data: UserTaskProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await development_service.update_task_progress(
        db,
        current_user,
        user_task_id,
        progress_data.progress_percentage,
        progress_data.notes,
    )


@router.get(
    "/manager-summary",
    response_model=ManagerDevelopmentSummary,
    dependencies=[Depends(require_mentor)],
)
async def get_manager_development_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await development_service.get_manager_summary(db, current_user)


@router.post(
    "/daily-tasks/assign",
    response_model=DailyTaskAssignResponse,
    dependencies=[Depends(require_mentor)],
)
async def assign_daily_tasks(
    request: DailyTaskAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await development_service.assign_daily_tasks(db, current_user, request)


@router.post(
    "/daily-tasks/reconcile",
    response_model=DailyTaskReconcileResponse,
    dependencies=[Depends(require_mentor)],
)
async def reconcile_daily_tasks(
    request: DailyTaskReconcileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_date, reports = await development_service.reconcile_daily_tasks(
        db,
        current_user,
        target_date=request.target_date,
        user_ids=request.user_ids,
    )
    return DailyTaskReconcileResponse(
        target_date=target_date,
        processed_count=len(reports),
        reports=reports,
    )


@router.post(
    "/evaluations/{user_id:uuid}",
    response_model=MemberEvaluationResponse,
    dependencies=[Depends(require_mentor)],
)
async def create_member_evaluation(
    user_id: UUID,
    manager_score: Optional[float] = Query(None, ge=0.0, le=100.0),
    notes: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select

    target_user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not target_user:
        from app.core.exceptions import NotFoundException

        raise NotFoundException("User not found")

    return await development_service.evaluate_member(
        db,
        target_user,
        created_by=current_user,
        manager_score=manager_score,
        notes=notes,
    )


@router.get(
    "/promotions",
    response_model=List[PromotionReviewResponse],
    dependencies=[Depends(require_mentor)],
)
async def list_promotion_reviews(
    status_filter: Optional[PromotionStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reviews = await development_service.list_promotions(db, current_user, status_filter)
    return [promotion_to_response(review) for review in reviews]


@router.post(
    "/promotions/{promotion_id:uuid}/approve",
    response_model=PromotionReviewResponse,
    dependencies=[Depends(require_mentor)],
)
async def approve_promotion(
    promotion_id: UUID,
    decision: PromotionDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    review = await development_service.decide_promotion(
        db,
        current_user,
        promotion_id,
        approved=True,
        notes=decision.manager_notes,
    )
    return promotion_to_response(review)


@router.post(
    "/promotions/{promotion_id:uuid}/reject",
    response_model=PromotionReviewResponse,
    dependencies=[Depends(require_mentor)],
)
async def reject_promotion(
    promotion_id: UUID,
    decision: PromotionDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    review = await development_service.decide_promotion(
        db,
        current_user,
        promotion_id,
        approved=False,
        notes=decision.manager_notes,
    )
    return promotion_to_response(review)
