"""Zalo OA Daily Task Quiz orchestration."""
from __future__ import annotations

import hashlib
import logging
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional
from uuid import UUID

import pytz
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.development import Question, QuestionStatus
from app.models.user import User, UserRole, UserStatus
from app.models.zalo import (
    ZaloDeliveryStatus,
    ZaloIntegrationConfig,
    ZaloLinkStatus,
    ZaloNotificationLog,
    ZaloProvider,
    ZaloQuizItem,
    ZaloQuizSession,
    ZaloQuizStatus,
    ZaloUserLink,
    ZaloWebhookEvent,
)
from app.schemas.zalo import ZaloIntegrationConfigUpdate
from app.services.question import question_service
from app.services.zalo_adapter import get_zalo_adapter, verify_webhook_signature

logger = logging.getLogger(__name__)
VN_TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")
CHOICES = {"A", "B", "C", "D"}


def normalize_choice(text: str) -> Optional[str]:
    match = re.match(r"^\s*([A-Da-d])(?:\s|[.)-]|$)", text or "")
    return match.group(1).upper() if match else None


def objective_score(selected: str, correct: str) -> tuple[bool, float]:
    is_correct = selected.strip().upper() == correct.strip().upper()
    return is_correct, 100.0 if is_correct else 0.0


def session_has_expired(expires_at: datetime, now: Optional[datetime] = None) -> bool:
    return expires_at <= (now or datetime.utcnow())


def webhook_event_key(payload: Dict[str, Any], raw_body: bytes) -> str:
    message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
    message_id = message.get("msg_id") or message.get("message_id")
    event_name = str(payload.get("event_name") or "unknown")
    if message_id:
        return f"{event_name}:{message_id}"
    return f"{event_name}:{hashlib.sha256(raw_body).hexdigest()}"


class ZaloQuizService:
    async def get_config(self, db: AsyncSession) -> ZaloIntegrationConfig:
        config = (await db.execute(select(ZaloIntegrationConfig).limit(1))).scalar_one_or_none()
        if config:
            return config
        try:
            provider = ZaloProvider(settings.ZALO_PROVIDER)
        except ValueError:
            provider = ZaloProvider.MOCK
        config = ZaloIntegrationConfig(provider=provider)
        db.add(config)
        await db.flush()
        return config

    @staticmethod
    def is_effectively_enabled(config: ZaloIntegrationConfig) -> bool:
        return bool(settings.ZALO_INTEGRATION_ENABLED and config.enabled)

    @staticmethod
    def oa_is_configured() -> bool:
        return all(
            [
                settings.ZALO_APP_ID,
                settings.ZALO_APP_SECRET,
                settings.ZALO_OA_ID,
                settings.ZALO_OA_SECRET_KEY,
                settings.ZALO_OA_ACCESS_TOKEN,
            ]
        )

    def config_response(self, config: ZaloIntegrationConfig) -> Dict[str, Any]:
        base_url = settings.ZALO_WEB_APP_URL.rstrip("/")
        return {
            "id": config.id,
            "enabled": config.enabled,
            "environment_enabled": settings.ZALO_INTEGRATION_ENABLED,
            "effective_enabled": self.is_effectively_enabled(config),
            "provider": config.provider,
            "send_hour": config.send_hour,
            "send_minute": config.send_minute,
            "reminder_hour": config.reminder_hour,
            "reminder_minute": config.reminder_minute,
            "quiz_size": config.quiz_size,
            "session_ttl_minutes": config.session_ttl_minutes,
            "send_window_days": config.send_window_days,
            "max_retries": config.max_retries,
            "oa_configured": self.oa_is_configured(),
            "webhook_url": f"{base_url}/api/v1/zalo/webhook",
            "web_app_url": base_url,
            "updated_at": config.updated_at,
        }

    async def update_config(
        self,
        db: AsyncSession,
        admin: User,
        data: ZaloIntegrationConfigUpdate,
    ) -> ZaloIntegrationConfig:
        config = await self.get_config(db)
        values = data.model_dump(exclude_unset=True)
        provider = values.get("provider", config.provider)
        if provider == ZaloProvider.ZALO_OA and values.get("enabled", config.enabled) and not self.oa_is_configured():
            raise BadRequestException("Zalo OA credentials are incomplete")
        for field, value in values.items():
            setattr(config, field, value)
        config.updated_by_id = admin.id
        config.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(config)
        return config

    async def get_link(self, db: AsyncSession, user: User) -> Optional[ZaloUserLink]:
        return (
            await db.execute(select(ZaloUserLink).where(ZaloUserLink.user_id == user.id))
        ).scalar_one_or_none()

    def link_response(
        self,
        config: ZaloIntegrationConfig,
        link: Optional[ZaloUserLink],
        link_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        oa_url = f"https://zalo.me/{settings.ZALO_OA_ID}" if settings.ZALO_OA_ID else None
        if link is None:
            return {
                "status": ZaloLinkStatus.REVOKED,
                "consent_granted": False,
                "notifications_enabled": False,
                "provider": config.provider,
                "oa_url": oa_url,
            }
        return {
            "status": link.status,
            "consent_granted": link.consent_granted,
            "notifications_enabled": link.notifications_enabled,
            "linked_at": link.linked_at,
            "last_interaction_at": link.last_interaction_at,
            "link_code": link_code,
            "link_expires_at": link.link_expires_at if link_code else None,
            "oa_url": oa_url,
            "provider": config.provider,
        }

    async def create_link_intent(
        self,
        db: AsyncSession,
        user: User,
        consent_granted: bool,
    ) -> tuple[ZaloIntegrationConfig, ZaloUserLink, Optional[str]]:
        if not consent_granted:
            raise BadRequestException("Consent is required before linking Zalo")
        config = await self.get_config(db)
        link = await self.get_link(db, user)
        now = datetime.utcnow()
        if link is None:
            link = ZaloUserLink(user_id=user.id)
            db.add(link)

        link.consent_granted = True
        link.notifications_enabled = True
        link.revoked_at = None
        link.updated_at = now

        if config.provider == ZaloProvider.MOCK:
            link.zalo_user_id = f"mock-{user.id}"
            link.status = ZaloLinkStatus.LINKED
            link.linked_at = now
            link.last_interaction_at = now
            link.link_token_hash = None
            link.link_expires_at = None
            await db.commit()
            await db.refresh(link)
            return config, link, None

        code = secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:10].upper()
        link.status = ZaloLinkStatus.PENDING
        link.link_token_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
        link.link_expires_at = now + timedelta(minutes=settings.ZALO_LINK_TOKEN_MINUTES)
        await db.commit()
        await db.refresh(link)
        return config, link, code

    async def set_notification_preference(
        self,
        db: AsyncSession,
        user: User,
        enabled: bool,
    ) -> ZaloUserLink:
        link = await self.get_link(db, user)
        if not link or link.status != ZaloLinkStatus.LINKED:
            raise NotFoundException("Zalo account is not linked")
        link.notifications_enabled = enabled
        link.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(link)
        return link

    async def revoke_link(self, db: AsyncSession, user: User) -> ZaloUserLink:
        link = await self.get_link(db, user)
        if not link:
            raise NotFoundException("Zalo account is not linked")
        link.status = ZaloLinkStatus.REVOKED
        link.consent_granted = False
        link.notifications_enabled = False
        link.zalo_user_id = None
        link.link_token_hash = None
        link.link_expires_at = None
        link.revoked_at = datetime.utcnow()
        await db.commit()
        await db.refresh(link)
        return link

    @staticmethod
    def can_send(link: ZaloUserLink, config: ZaloIntegrationConfig, now: Optional[datetime] = None) -> bool:
        if (
            link.status != ZaloLinkStatus.LINKED
            or not link.consent_granted
            or not link.notifications_enabled
            or not link.zalo_user_id
        ):
            return False
        if config.provider == ZaloProvider.MOCK:
            return True
        if not link.last_interaction_at:
            return False
        return link.last_interaction_at >= (now or datetime.utcnow()) - timedelta(days=config.send_window_days)

    async def _select_questions(
        self,
        db: AsyncSession,
        user: User,
        limit: int,
    ) -> list[Question]:
        await question_service.ensure_system_question_bank(db)
        query = (
            select(Question)
            .where(
                Question.status == QuestionStatus.ACTIVE,
                Question.question_type == "multiple_choice",
                Question.options.isnot(None),
                Question.correct_option.isnot(None),
                or_(Question.target_member_level == user.member_level, Question.is_baseline.is_(True)),
            )
            .order_by(func.random())
            .limit(limit)
        )
        questions = list((await db.execute(query)).scalars().all())
        return [
            question
            for question in questions
            if isinstance(question.options, dict)
            and set(question.options).issuperset(CHOICES)
            and (question.correct_option or "").upper() in CHOICES
        ]

    async def create_session(
        self,
        db: AsyncSession,
        user: User,
        config: ZaloIntegrationConfig,
        session_date: Optional[date] = None,
    ) -> ZaloQuizSession:
        target_date = session_date or datetime.now(VN_TIMEZONE).date()
        existing = (
            await db.execute(
                select(ZaloQuizSession)
                .options(selectinload(ZaloQuizSession.items))
                .where(
                    ZaloQuizSession.user_id == user.id,
                    ZaloQuizSession.session_date == target_date,
                )
            )
        ).scalar_one_or_none()
        if existing:
            return existing

        questions = await self._select_questions(db, user, config.quiz_size)
        if not questions:
            raise BadRequestException("No active multiple-choice questions are available")

        now = datetime.utcnow()
        session = ZaloQuizSession(
            user_id=user.id,
            session_date=target_date,
            total_questions=len(questions),
            expires_at=now + timedelta(minutes=config.session_ttl_minutes),
        )
        db.add(session)
        await db.flush()
        for position, question in enumerate(questions, start=1):
            db.add(
                ZaloQuizItem(
                    session_id=session.id,
                    question_id=question.id,
                    position=position,
                    prompt=question.question,
                    options=dict(question.options),
                    correct_option=question.correct_option.upper(),
                )
            )
        await db.flush()
        await db.refresh(session, attribute_names=["items"])
        return session

    @staticmethod
    def format_question(session: ZaloQuizSession, item: ZaloQuizItem) -> str:
        lines = [f"TLMS Daily Quiz {item.position}/{session.total_questions}", "", item.prompt]
        for choice in ("A", "B", "C", "D"):
            lines.append(f"{choice}. {item.options.get(choice, '')}")
        lines.extend(
            [
                "",
                "Tra loi bang A, B, C hoac D.",
                f"Theo doi tien do: {settings.ZALO_WEB_APP_URL.rstrip('/')}/candidate/questions",
            ]
        )
        return "\n".join(lines)

    async def _queue_and_send(
        self,
        db: AsyncSession,
        link: ZaloUserLink,
        config: ZaloIntegrationConfig,
        event_type: str,
        idempotency_key: str,
        text: str,
        session: Optional[ZaloQuizSession] = None,
    ) -> ZaloNotificationLog:
        existing = (
            await db.execute(
                select(ZaloNotificationLog).where(ZaloNotificationLog.idempotency_key == idempotency_key)
            )
        ).scalar_one_or_none()
        if existing:
            return existing

        log = ZaloNotificationLog(
            user_id=link.user_id,
            link_id=link.id,
            session_id=session.id if session else None,
            event_type=event_type,
            idempotency_key=idempotency_key,
            payload={"text": text[:2000]},
            max_retries=config.max_retries,
        )
        db.add(log)
        await db.flush()

        if not self.can_send(link, config):
            log.status = ZaloDeliveryStatus.SKIPPED
            log.last_error = "Consent, link status, or Zalo interaction window does not allow sending"
            return log

        try:
            result = await get_zalo_adapter(config.provider).send_text(link.zalo_user_id, text)
            log.status = ZaloDeliveryStatus.SENT
            log.external_message_id = result.external_message_id
            log.response = result.response
            log.sent_at = datetime.utcnow()
            log.last_error = None
        except Exception as exc:
            logger.warning("Zalo delivery failed for log %s: %s", log.id, exc)
            log.status = ZaloDeliveryStatus.FAILED
            log.retry_count = 1
            log.next_retry_at = datetime.utcnow() + timedelta(minutes=2)
            log.last_error = str(exc)[:1000]
        return log

    async def dispatch_daily(self, db: AsyncSession) -> Dict[str, int]:
        config = await self.get_config(db)
        result = {"considered": 0, "sessions_created": 0, "messages_sent": 0, "skipped": 0, "failed": 0}
        if not self.is_effectively_enabled(config):
            return result

        links = list(
            (
                await db.execute(
                    select(ZaloUserLink)
                    .options(selectinload(ZaloUserLink.user))
                    .where(
                        ZaloUserLink.status == ZaloLinkStatus.LINKED,
                        ZaloUserLink.consent_granted.is_(True),
                        ZaloUserLink.notifications_enabled.is_(True),
                    )
                )
            ).scalars().all()
        )
        today = datetime.now(VN_TIMEZONE).date()
        for link in links:
            user = link.user
            if not user or user.status != UserStatus.ACTIVE or not any(
                role in (user.roles or []) for role in (UserRole.CANDIDATE.value, UserRole.MEMBER.value)
            ):
                continue
            result["considered"] += 1
            if not self.can_send(link, config):
                result["skipped"] += 1
                continue
            try:
                previous = (
                    await db.execute(
                        select(ZaloQuizSession).where(
                            ZaloQuizSession.user_id == user.id,
                            ZaloQuizSession.session_date == today,
                        )
                    )
                ).scalar_one_or_none()
                session = await self.create_session(db, user, config, today)
                if previous is None:
                    result["sessions_created"] += 1
                if session.status != ZaloQuizStatus.ACTIVE:
                    result["skipped"] += 1
                    continue
                item = next((item for item in session.items if item.position == session.current_position), None)
                if not item:
                    result["skipped"] += 1
                    continue
                delivery = await self._queue_and_send(
                    db,
                    link,
                    config,
                    "daily_quiz",
                    f"daily:{session.id}:{item.position}",
                    self.format_question(session, item),
                    session,
                )
                if delivery.status == ZaloDeliveryStatus.SENT:
                    result["messages_sent"] += 1
                elif delivery.status == ZaloDeliveryStatus.FAILED:
                    result["failed"] += 1
                else:
                    result["skipped"] += 1
            except Exception as exc:
                result["failed"] += 1
                logger.exception("Unable to dispatch Zalo quiz for user %s: %s", user.id, exc)
        await db.commit()
        return result

    async def send_reminders(self, db: AsyncSession) -> Dict[str, int]:
        config = await self.get_config(db)
        result = {"considered": 0, "sessions_created": 0, "messages_sent": 0, "skipped": 0, "failed": 0}
        if not self.is_effectively_enabled(config):
            return result
        sessions = list(
            (
                await db.execute(
                    select(ZaloQuizSession)
                    .options(selectinload(ZaloQuizSession.items), selectinload(ZaloQuizSession.user))
                    .where(
                        ZaloQuizSession.session_date == datetime.now(VN_TIMEZONE).date(),
                        ZaloQuizSession.status == ZaloQuizStatus.ACTIVE,
                    )
                )
            ).scalars().all()
        )
        for session in sessions:
            result["considered"] += 1
            link = (
                await db.execute(select(ZaloUserLink).where(ZaloUserLink.user_id == session.user_id))
            ).scalar_one_or_none()
            if not link or not self.can_send(link, config):
                result["skipped"] += 1
                continue
            item = next((item for item in session.items if item.position == session.current_position), None)
            if not item:
                continue
            delivery = await self._queue_and_send(
                db,
                link,
                config,
                "reminder",
                f"reminder:{session.id}:{session.current_position}",
                "Ban chua hoan thanh Daily Quiz hom nay.\n\n" + self.format_question(session, item),
                session,
            )
            if delivery.status == ZaloDeliveryStatus.SENT:
                result["messages_sent"] += 1
            elif delivery.status == ZaloDeliveryStatus.FAILED:
                result["failed"] += 1
            else:
                result["skipped"] += 1
        await db.commit()
        return result

    async def expire_sessions(self, db: AsyncSession) -> int:
        sessions = list(
            (
                await db.execute(
                    select(ZaloQuizSession).where(
                        ZaloQuizSession.status == ZaloQuizStatus.ACTIVE,
                        ZaloQuizSession.expires_at <= datetime.utcnow(),
                    )
                )
            ).scalars().all()
        )
        for session in sessions:
            session.status = ZaloQuizStatus.EXPIRED
            session.updated_at = datetime.utcnow()
        if sessions:
            await db.commit()
        return len(sessions)

    async def retry_failed(self, db: AsyncSession) -> int:
        config = await self.get_config(db)
        if not self.is_effectively_enabled(config):
            return 0
        logs = list(
            (
                await db.execute(
                    select(ZaloNotificationLog)
                    .options(selectinload(ZaloNotificationLog.link))
                    .where(
                        ZaloNotificationLog.status == ZaloDeliveryStatus.FAILED,
                        ZaloNotificationLog.retry_count < ZaloNotificationLog.max_retries,
                        ZaloNotificationLog.next_retry_at <= datetime.utcnow(),
                    )
                    .limit(50)
                )
            ).scalars().all()
        )
        sent = 0
        for log in logs:
            link = log.link
            if not link or not self.can_send(link, config):
                log.status = ZaloDeliveryStatus.SKIPPED
                log.last_error = "No longer eligible for Zalo delivery"
                continue
            try:
                result = await get_zalo_adapter(config.provider).send_text(
                    link.zalo_user_id,
                    str((log.payload or {}).get("text") or ""),
                )
                log.status = ZaloDeliveryStatus.SENT
                log.response = result.response
                log.external_message_id = result.external_message_id
                log.sent_at = datetime.utcnow()
                log.last_error = None
                sent += 1
            except Exception as exc:
                log.retry_count += 1
                log.last_error = str(exc)[:1000]
                log.next_retry_at = datetime.utcnow() + timedelta(minutes=min(30, 2 ** log.retry_count))
        await db.commit()
        return sent

    async def _complete_link_from_message(
        self,
        db: AsyncSession,
        sender_id: str,
        text: str,
    ) -> Optional[ZaloUserLink]:
        match = re.match(r"^\s*TLMS\s+LINK\s+([A-Za-z0-9]+)\s*$", text or "", re.IGNORECASE)
        if not match:
            return None
        token_hash = hashlib.sha256(match.group(1).upper().encode("utf-8")).hexdigest()
        link = (
            await db.execute(
                select(ZaloUserLink).where(
                    ZaloUserLink.link_token_hash == token_hash,
                    ZaloUserLink.status == ZaloLinkStatus.PENDING,
                    ZaloUserLink.link_expires_at > datetime.utcnow(),
                )
            )
        ).scalar_one_or_none()
        if not link:
            return None
        collision = (
            await db.execute(
                select(ZaloUserLink).where(
                    ZaloUserLink.zalo_user_id == sender_id,
                    ZaloUserLink.id != link.id,
                    ZaloUserLink.status == ZaloLinkStatus.LINKED,
                )
            )
        ).scalar_one_or_none()
        if collision:
            raise BadRequestException("This Zalo account is already linked")
        now = datetime.utcnow()
        link.zalo_user_id = sender_id
        link.status = ZaloLinkStatus.LINKED
        link.linked_at = now
        link.last_interaction_at = now
        link.link_token_hash = None
        link.link_expires_at = None
        return link

    async def _process_choice(
        self,
        db: AsyncSession,
        link: ZaloUserLink,
        choice: str,
        config: ZaloIntegrationConfig,
    ) -> str:
        session = (
            await db.execute(
                select(ZaloQuizSession)
                .options(
                    selectinload(ZaloQuizSession.items).selectinload(ZaloQuizItem.question),
                    selectinload(ZaloQuizSession.user),
                )
                .where(
                    ZaloQuizSession.user_id == link.user_id,
                    ZaloQuizSession.status == ZaloQuizStatus.ACTIVE,
                )
                .order_by(ZaloQuizSession.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if not session:
            return f"Ban chua co Daily Quiz dang hoat dong. Mo {settings.ZALO_WEB_APP_URL.rstrip('/')}/candidate/questions"
        if session_has_expired(session.expires_at):
            session.status = ZaloQuizStatus.EXPIRED
            return "Phien Daily Quiz da het han. Ket qua khong duoc tinh XP."

        item = next((value for value in session.items if value.position == session.current_position), None)
        if not item or item.answered_at:
            return "Cau tra loi nay da duoc ghi nhan."
        is_correct, _ = objective_score(choice, item.correct_option)
        item.selected_option = choice
        item.is_correct = is_correct
        item.answered_at = datetime.utcnow()
        _, points_delta = await question_service.record_objective_answer(
            db,
            session.user,
            item.question,
            choice,
        )
        item.points_awarded = points_delta
        session.answered_count += 1
        session.correct_count += 1 if is_correct else 0
        session.xp_awarded += points_delta
        session.score = round((session.correct_count / session.total_questions) * 100.0, 1)

        feedback = "Chinh xac" if is_correct else f"Chua dung. Dap an dung la {item.correct_option}"
        if session.answered_count >= session.total_questions:
            session.status = ZaloQuizStatus.COMPLETED
            session.completed_at = datetime.utcnow()
            if not session.attendance_applied:
                session.user.discipline_score = min(
                    100.0,
                    float(session.user.discipline_score or 0.0) + settings.DAILY_DISCIPLINE_COMPLETE_BONUS,
                )
                session.user.reliability_score = min(
                    100.0,
                    float(session.user.reliability_score or 0.0) + settings.DAILY_RELIABILITY_COMPLETE_BONUS,
                )
                session.attendance_applied = True
            return (
                f"{feedback}. Hoan thanh {session.correct_count}/{session.total_questions}, "
                f"diem {session.score:.0f}/100, +{session.xp_awarded} XP.\n"
                f"Xem ket qua: {settings.ZALO_WEB_APP_URL.rstrip('/')}/candidate/questions"
            )

        session.current_position += 1
        next_item = next((value for value in session.items if value.position == session.current_position), None)
        if not next_item:
            return feedback
        return f"{feedback}. +{points_delta} XP.\n\n{self.format_question(session, next_item)}"

    async def process_webhook(
        self,
        db: AsyncSession,
        payload: Dict[str, Any],
        raw_body: bytes,
        signature_header: str,
    ) -> Dict[str, Any]:
        config = await self.get_config(db)
        if not self.is_effectively_enabled(config):
            raise BadRequestException("Zalo integration is disabled")

        timestamp = str(payload.get("timestamp") or "")
        app_id = str(payload.get("app_id") or "")
        signature_valid = config.provider == ZaloProvider.MOCK
        if config.provider == ZaloProvider.ZALO_OA:
            signature_valid = verify_webhook_signature(
                raw_body,
                signature_header,
                app_id,
                timestamp,
                settings.ZALO_OA_SECRET_KEY,
            )
            if app_id != settings.ZALO_APP_ID:
                signature_valid = False
            try:
                event_time = datetime.fromtimestamp(int(timestamp) / 1000, tz=timezone.utc)
                skew = abs((datetime.now(timezone.utc) - event_time).total_seconds())
                if skew > settings.ZALO_WEBHOOK_MAX_SKEW_SECONDS:
                    signature_valid = False
            except (TypeError, ValueError, OSError):
                signature_valid = False
        if not signature_valid:
            raise BadRequestException("Invalid Zalo webhook signature")

        key = webhook_event_key(payload, raw_body)
        duplicate = (
            await db.execute(select(ZaloWebhookEvent).where(ZaloWebhookEvent.event_key == key))
        ).scalar_one_or_none()
        if duplicate:
            return {"success": True, "duplicate": True, "action": "duplicate"}

        sender = payload.get("sender") if isinstance(payload.get("sender"), dict) else {}
        message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
        sender_id = str(sender.get("id") or "")
        text = str(message.get("text") or "").strip()
        event = ZaloWebhookEvent(
            event_key=key,
            event_name=str(payload.get("event_name") or "unknown"),
            sender_hash=hashlib.sha256(sender_id.encode("utf-8")).hexdigest() if sender_id else None,
            payload_digest=hashlib.sha256(raw_body).hexdigest(),
            signature_valid=True,
        )
        db.add(event)
        await db.flush()

        if not sender_id or not text or payload.get("event_name") != "user_send_text":
            event.processing_status = "ignored"
            event.processed_at = datetime.utcnow()
            await db.commit()
            return {"success": True, "duplicate": False, "action": "ignored"}

        link = await self._complete_link_from_message(db, sender_id, text)
        action = "linked" if link else "ignored"
        response_text: Optional[str] = None
        if link:
            response_text = f"Lien ket TLMS thanh cong. Daily Quiz se duoc gui tai day. {settings.ZALO_WEB_APP_URL.rstrip('/')}"
        else:
            link = (
                await db.execute(
                    select(ZaloUserLink).where(
                        ZaloUserLink.zalo_user_id == sender_id,
                        ZaloUserLink.status == ZaloLinkStatus.LINKED,
                    )
                )
            ).scalar_one_or_none()
            if link:
                link.last_interaction_at = datetime.utcnow()
                choice = normalize_choice(text)
                if choice:
                    response_text = await self._process_choice(db, link, choice, config)
                    action = "answer"

        if link and response_text:
            await self._queue_and_send(
                db,
                link,
                config,
                "webhook_reply",
                f"reply:{key}",
                response_text,
            )
        event.processing_status = "processed"
        event.processed_at = datetime.utcnow()
        await db.commit()
        return {"success": True, "duplicate": False, "action": action}

    async def run_scheduled_jobs(self, db: AsyncSession) -> None:
        config = await self.get_config(db)
        await self.expire_sessions(db)
        await self.retry_failed(db)
        if not self.is_effectively_enabled(config):
            return
        now = datetime.now(VN_TIMEZONE)
        if (now.hour, now.minute) == (config.send_hour, config.send_minute):
            await self.dispatch_daily(db)
        if (now.hour, now.minute) == (config.reminder_hour, config.reminder_minute):
            await self.send_reminders(db)

    async def admin_dashboard(self, db: AsyncSession) -> Dict[str, Any]:
        config = await self.get_config(db)
        today = datetime.now(VN_TIMEZONE).date()
        linked_users = (
            await db.execute(
                select(func.count(ZaloUserLink.id)).where(ZaloUserLink.status == ZaloLinkStatus.LINKED)
            )
        ).scalar() or 0
        opted_in = (
            await db.execute(
                select(func.count(ZaloUserLink.id)).where(
                    ZaloUserLink.status == ZaloLinkStatus.LINKED,
                    ZaloUserLink.consent_granted.is_(True),
                    ZaloUserLink.notifications_enabled.is_(True),
                )
            )
        ).scalar() or 0
        active = (
            await db.execute(
                select(func.count(ZaloQuizSession.id)).where(ZaloQuizSession.status == ZaloQuizStatus.ACTIVE)
            )
        ).scalar() or 0
        completed_today = (
            await db.execute(
                select(func.count(ZaloQuizSession.id)).where(
                    ZaloQuizSession.session_date == today,
                    ZaloQuizSession.status == ZaloQuizStatus.COMPLETED,
                )
            )
        ).scalar() or 0
        failed = (
            await db.execute(
                select(func.count(ZaloNotificationLog.id)).where(
                    ZaloNotificationLog.status == ZaloDeliveryStatus.FAILED
                )
            )
        ).scalar() or 0
        sessions = list(
            (
                await db.execute(
                    select(ZaloQuizSession)
                    .options(selectinload(ZaloQuizSession.items), selectinload(ZaloQuizSession.user))
                    .order_by(ZaloQuizSession.created_at.desc())
                    .limit(30)
                )
            ).scalars().all()
        )
        deliveries = list(
            (
                await db.execute(
                    select(ZaloNotificationLog)
                    .options(selectinload(ZaloNotificationLog.user))
                    .order_by(ZaloNotificationLog.created_at.desc())
                    .limit(50)
                )
            ).scalars().all()
        )
        return {
            "config": self.config_response(config),
            "linked_users": linked_users,
            "opted_in_users": opted_in,
            "active_sessions": active,
            "completed_today": completed_today,
            "failed_deliveries": failed,
            "sessions": [
                {
                    "id": session.id,
                    "user_id": session.user_id,
                    "user_email": session.user.email if session.user else None,
                    "session_date": session.session_date,
                    "status": session.status,
                    "total_questions": session.total_questions,
                    "answered_count": session.answered_count,
                    "correct_count": session.correct_count,
                    "score": session.score,
                    "xp_awarded": session.xp_awarded,
                    "expires_at": session.expires_at,
                    "completed_at": session.completed_at,
                    "items": [
                        {
                            "position": item.position,
                            "prompt": item.prompt,
                            "options": item.options,
                            "selected_option": item.selected_option,
                            "is_correct": item.is_correct,
                            "points_awarded": item.points_awarded,
                        }
                        for item in session.items
                    ],
                }
                for session in sessions
            ],
            "deliveries": [
                {
                    "id": delivery.id,
                    "user_id": delivery.user_id,
                    "user_email": delivery.user.email if delivery.user else None,
                    "event_type": delivery.event_type,
                    "status": delivery.status,
                    "retry_count": delivery.retry_count,
                    "max_retries": delivery.max_retries,
                    "last_error": delivery.last_error,
                    "sent_at": delivery.sent_at,
                    "created_at": delivery.created_at,
                }
                for delivery in deliveries
            ],
        }


zalo_quiz_service = ZaloQuizService()
