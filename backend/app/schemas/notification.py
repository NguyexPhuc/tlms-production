"""Notification schemas."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.development import NotificationChannel


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    event_type: str
    title: str
    message: str
    channel: NotificationChannel
    payload: Optional[Dict[str, Any]] = None
    actor_id: Optional[UUID] = None
    read_at: Optional[datetime] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int
    unread_count: int
