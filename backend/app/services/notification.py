"""Notification service."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.development import Notification, NotificationChannel
from app.models.user import User


class NotificationService:
    """Create and manage persisted in-app notifications."""

    async def create_notification(
        self,
        db: AsyncSession,
        user_id: UUID,
        event_type: str,
        title: str,
        message: str,
        actor_id: Optional[UUID] = None,
        payload: Optional[Dict[str, Any]] = None,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        commit: bool = False,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            event_type=event_type,
            title=title,
            message=message,
            actor_id=actor_id,
            payload=payload,
            channel=channel,
        )
        db.add(notification)
        await db.flush()

        if commit:
            await db.commit()
            await db.refresh(notification)

        return notification

    async def list_for_user(
        self,
        db: AsyncSession,
        user: User,
        unread_only: bool = False,
        limit: int = 50,
    ) -> tuple[List[Notification], int]:
        query = select(Notification).where(Notification.user_id == user.id)
        unread_query = select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.read_at.is_(None),
        )

        if unread_only:
            query = query.where(Notification.read_at.is_(None))

        query = query.order_by(Notification.created_at.desc()).limit(limit)

        notifications = (await db.execute(query)).scalars().all()
        unread_count = (await db.execute(unread_query)).scalar() or 0
        return list(notifications), unread_count

    async def mark_read(
        self,
        db: AsyncSession,
        user: User,
        notification_id: UUID,
    ) -> Notification:
        notification = (
            await db.execute(
                select(Notification).where(
                    Notification.id == notification_id,
                    Notification.user_id == user.id,
                )
            )
        ).scalar_one_or_none()

        if not notification:
            raise NotFoundException("Notification not found")

        if notification.read_at is None:
            notification.read_at = datetime.utcnow()
            await db.commit()
            await db.refresh(notification)

        return notification

    async def mark_all_read(self, db: AsyncSession, user: User) -> int:
        notifications = (
            await db.execute(
                select(Notification).where(
                    Notification.user_id == user.id,
                    Notification.read_at.is_(None),
                )
            )
        ).scalars().all()

        now = datetime.utcnow()
        for notification in notifications:
            notification.read_at = now

        await db.commit()
        return len(notifications)


notification_service = NotificationService()
