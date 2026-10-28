"""API schemas for Zalo OA Daily Task Quiz."""
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.zalo import ZaloDeliveryStatus, ZaloLinkStatus, ZaloProvider, ZaloQuizStatus


class ZaloLinkIntentRequest(BaseModel):
    consent_granted: bool


class ZaloNotificationPreferenceRequest(BaseModel):
    enabled: bool


class ZaloLinkResponse(BaseModel):
    status: ZaloLinkStatus
    consent_granted: bool
    notifications_enabled: bool
    linked_at: Optional[datetime] = None
    last_interaction_at: Optional[datetime] = None
    link_code: Optional[str] = None
    link_expires_at: Optional[datetime] = None
    oa_url: Optional[str] = None
    provider: ZaloProvider

    class Config:
        from_attributes = True
        use_enum_values = True


class ZaloIntegrationConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    provider: Optional[ZaloProvider] = None
    send_hour: Optional[int] = Field(None, ge=0, le=23)
    send_minute: Optional[int] = Field(None, ge=0, le=59)
    reminder_hour: Optional[int] = Field(None, ge=0, le=23)
    reminder_minute: Optional[int] = Field(None, ge=0, le=59)
    quiz_size: Optional[int] = Field(None, ge=1, le=20)
    session_ttl_minutes: Optional[int] = Field(None, ge=15, le=1440)
    send_window_days: Optional[int] = Field(None, ge=1, le=7)
    max_retries: Optional[int] = Field(None, ge=0, le=10)


class ZaloIntegrationConfigResponse(BaseModel):
    id: UUID
    enabled: bool
    environment_enabled: bool
    effective_enabled: bool
    provider: ZaloProvider
    send_hour: int
    send_minute: int
    reminder_hour: int
    reminder_minute: int
    quiz_size: int
    session_ttl_minutes: int
    send_window_days: int
    max_retries: int
    oa_configured: bool
    webhook_url: str
    web_app_url: str
    updated_at: datetime

    class Config:
        use_enum_values = True


class ZaloQuizItemResponse(BaseModel):
    position: int
    prompt: str
    options: Dict[str, str]
    selected_option: Optional[str] = None
    is_correct: Optional[bool] = None
    points_awarded: int


class ZaloQuizSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_email: Optional[str] = None
    session_date: date
    status: ZaloQuizStatus
    total_questions: int
    answered_count: int
    correct_count: int
    score: float
    xp_awarded: int
    expires_at: datetime
    completed_at: Optional[datetime] = None
    items: List[ZaloQuizItemResponse] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class ZaloDeliveryLogResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    user_email: Optional[str] = None
    event_type: str
    status: ZaloDeliveryStatus
    retry_count: int
    max_retries: int
    last_error: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        use_enum_values = True


class ZaloAdminDashboardResponse(BaseModel):
    config: ZaloIntegrationConfigResponse
    linked_users: int
    opted_in_users: int
    active_sessions: int
    completed_today: int
    failed_deliveries: int
    sessions: List[ZaloQuizSessionResponse]
    deliveries: List[ZaloDeliveryLogResponse]


class ZaloDispatchResponse(BaseModel):
    considered: int
    sessions_created: int
    messages_sent: int
    skipped: int
    failed: int


class ZaloMockMessageRequest(BaseModel):
    user_id: UUID
    text: str = Field(..., min_length=1, max_length=2000)


class ZaloWebhookResponse(BaseModel):
    success: bool = True
    duplicate: bool = False
    action: str = "ignored"
