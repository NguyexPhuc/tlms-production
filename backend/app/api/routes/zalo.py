"""REST and webhook endpoints for the optional Zalo OA integration."""
import hmac
import json
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.user import User
from app.models.zalo import ZaloProvider
from app.schemas.zalo import (
    ZaloAdminDashboardResponse,
    ZaloDispatchResponse,
    ZaloIntegrationConfigResponse,
    ZaloIntegrationConfigUpdate,
    ZaloLinkIntentRequest,
    ZaloLinkResponse,
    ZaloMockMessageRequest,
    ZaloNotificationPreferenceRequest,
    ZaloWebhookResponse,
)
from app.services.zalo_quiz import zalo_quiz_service

router = APIRouter(prefix="/zalo", tags=["Zalo Daily Task Quiz"])


@router.get("/me", response_model=ZaloLinkResponse)
async def get_my_zalo_link(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = await zalo_quiz_service.get_config(db)
    link = await zalo_quiz_service.get_link(db, current_user)
    return zalo_quiz_service.link_response(config, link)


@router.post("/me/link-intent", response_model=ZaloLinkResponse)
async def create_zalo_link_intent(
    data: ZaloLinkIntentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config, link, code = await zalo_quiz_service.create_link_intent(
        db,
        current_user,
        data.consent_granted,
    )
    return zalo_quiz_service.link_response(config, link, code)


@router.patch("/me/notifications", response_model=ZaloLinkResponse)
async def update_zalo_notifications(
    data: ZaloNotificationPreferenceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = await zalo_quiz_service.get_config(db)
    link = await zalo_quiz_service.set_notification_preference(db, current_user, data.enabled)
    return zalo_quiz_service.link_response(config, link)


@router.delete("/me", response_model=ZaloLinkResponse)
async def revoke_zalo_link(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = await zalo_quiz_service.get_config(db)
    link = await zalo_quiz_service.revoke_link(db, current_user)
    return zalo_quiz_service.link_response(config, link)


@router.post("/webhook", response_model=ZaloWebhookResponse)
async def zalo_webhook(
    request: Request,
    x_zevent_signature: str = Header("", alias="X-ZEvent-Signature"),
    x_tlms_mock_secret: str = Header("", alias="X-TLMS-Mock-Secret"),
    db: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except (TypeError, ValueError) as exc:
        raise BadRequestException("Webhook body must be valid JSON") from exc
    config = await zalo_quiz_service.get_config(db)
    if config.provider == ZaloProvider.MOCK:
        if not settings.WEBHOOK_API_KEY or not hmac.compare_digest(x_tlms_mock_secret, settings.WEBHOOK_API_KEY):
            raise BadRequestException("Invalid mock webhook secret")
    return await zalo_quiz_service.process_webhook(db, payload, raw_body, x_zevent_signature)


@router.get("/admin/config", response_model=ZaloIntegrationConfigResponse)
async def get_zalo_config(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    config = await zalo_quiz_service.get_config(db)
    return zalo_quiz_service.config_response(config)


@router.patch("/admin/config", response_model=ZaloIntegrationConfigResponse)
async def update_zalo_config(
    data: ZaloIntegrationConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    config = await zalo_quiz_service.update_config(db, current_user, data)
    return zalo_quiz_service.config_response(config)


@router.get("/admin/dashboard", response_model=ZaloAdminDashboardResponse)
async def get_zalo_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await zalo_quiz_service.admin_dashboard(db)


@router.post("/admin/dispatch", response_model=ZaloDispatchResponse)
async def dispatch_zalo_quizzes(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await zalo_quiz_service.dispatch_daily(db)


@router.post("/admin/mock-message", response_model=ZaloWebhookResponse)
async def send_mock_zalo_message(
    data: ZaloMockMessageRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    config = await zalo_quiz_service.get_config(db)
    if config.provider != ZaloProvider.MOCK:
        raise BadRequestException("Mock messages are available only with the mock provider")
    user = await db.get(User, data.user_id)
    if not user:
        raise NotFoundException("User not found")
    link = await zalo_quiz_service.get_link(db, user)
    if not link or not link.zalo_user_id:
        raise NotFoundException("User has no linked mock Zalo account")
    payload = {
        "app_id": "mock",
        "sender": {"id": link.zalo_user_id},
        "recipient": {"id": "mock-oa"},
        "event_name": "user_send_text",
        "message": {"text": data.text, "msg_id": f"mock-{secrets.token_hex(10)}"},
        "timestamp": str(int(datetime.utcnow().timestamp() * 1000)),
    }
    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return await zalo_quiz_service.process_webhook(db, payload, raw_body, "")
