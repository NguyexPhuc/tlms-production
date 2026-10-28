"""Notification routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services.notification import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/me", response_model=NotificationListResponse)
async def get_my_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notifications, unread_count = await notification_service.list_for_user(
        db,
        current_user,
        unread_only=unread_only,
        limit=limit,
    )
    return NotificationListResponse(
        notifications=notifications,
        total=len(notifications),
        unread_count=unread_count,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await notification_service.mark_read(db, current_user, notification_id)


@router.patch("/read-all")
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = await notification_service.mark_all_read(db, current_user)
    return {"success": True, "updated_count": count}
