"""Persistence models for the optional Zalo OA Daily Task Quiz module."""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ZaloProvider(str, Enum):
    MOCK = "mock"
    ZALO_OA = "zalo_oa"


class ZaloLinkStatus(str, Enum):
    PENDING = "pending"
    LINKED = "linked"
    REVOKED = "revoked"


class ZaloQuizStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"


class ZaloDeliveryStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class ZaloIntegrationConfig(Base):
    """Runtime-safe settings. Credentials remain environment-only."""
    __tablename__ = "zalo_integration_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enabled = Column(Boolean, default=False, nullable=False)
    provider = Column(
        SQLEnum(ZaloProvider, values_callable=lambda values: [item.value for item in values]),
        default=ZaloProvider.MOCK,
        nullable=False,
    )
    send_hour = Column(Integer, default=8, nullable=False)
    send_minute = Column(Integer, default=0, nullable=False)
    reminder_hour = Column(Integer, default=18, nullable=False)
    reminder_minute = Column(Integer, default=0, nullable=False)
    quiz_size = Column(Integer, default=5, nullable=False)
    session_ttl_minutes = Column(Integer, default=720, nullable=False)
    send_window_days = Column(Integer, default=7, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    updated_by = relationship("User", foreign_keys=[updated_by_id])


class ZaloUserLink(Base):
    """Consent and OA UID mapping for one TLMS user."""
    __tablename__ = "zalo_user_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    zalo_user_id = Column(String(100), unique=True, index=True, nullable=True)
    status = Column(
        SQLEnum(ZaloLinkStatus, values_callable=lambda values: [item.value for item in values]),
        default=ZaloLinkStatus.PENDING,
        nullable=False,
    )
    consent_granted = Column(Boolean, default=False, nullable=False)
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    link_token_hash = Column(String(64), unique=True, nullable=True)
    link_expires_at = Column(DateTime, nullable=True)
    last_interaction_at = Column(DateTime, nullable=True)
    linked_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", backref="zalo_link", uselist=False)


class ZaloQuizSession(Base):
    """Daily quiz attempt sent through Zalo."""
    __tablename__ = "zalo_quiz_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "session_date", name="uq_zalo_quiz_sessions_user_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_date = Column(Date, nullable=False)
    status = Column(
        SQLEnum(ZaloQuizStatus, values_callable=lambda values: [item.value for item in values]),
        default=ZaloQuizStatus.ACTIVE,
        nullable=False,
    )
    total_questions = Column(Integer, default=0, nullable=False)
    current_position = Column(Integer, default=1, nullable=False)
    answered_count = Column(Integer, default=0, nullable=False)
    correct_count = Column(Integer, default=0, nullable=False)
    score = Column(Float, default=0.0, nullable=False)
    xp_awarded = Column(Integer, default=0, nullable=False)
    attendance_applied = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", backref="zalo_quiz_sessions")
    items = relationship(
        "ZaloQuizItem",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ZaloQuizItem.position",
    )


class ZaloQuizItem(Base):
    """Question snapshot so later bank edits do not alter an active quiz."""
    __tablename__ = "zalo_quiz_items"
    __table_args__ = (
        UniqueConstraint("session_id", "position", name="uq_zalo_quiz_items_session_position"),
        UniqueConstraint("session_id", "question_id", name="uq_zalo_quiz_items_session_question"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("zalo_quiz_sessions.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False)
    position = Column(Integer, nullable=False)
    prompt = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)
    correct_option = Column(String(1), nullable=False)
    selected_option = Column(String(1), nullable=True)
    is_correct = Column(Boolean, nullable=True)
    points_awarded = Column(Integer, default=0, nullable=False)
    answered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("ZaloQuizSession", back_populates="items")
    question = relationship("Question")


class ZaloNotificationLog(Base):
    """Idempotent delivery queue and operational audit log."""
    __tablename__ = "zalo_notification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    link_id = Column(UUID(as_uuid=True), ForeignKey("zalo_user_links.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("zalo_quiz_sessions.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(50), nullable=False)
    idempotency_key = Column(String(180), unique=True, nullable=False)
    status = Column(
        SQLEnum(ZaloDeliveryStatus, values_callable=lambda values: [item.value for item in values]),
        default=ZaloDeliveryStatus.PENDING,
        nullable=False,
    )
    payload = Column(JSON, nullable=False, default=dict)
    response = Column(JSON, nullable=True)
    external_message_id = Column(String(150), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    next_retry_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    link = relationship("ZaloUserLink", foreign_keys=[link_id])
    session = relationship("ZaloQuizSession", foreign_keys=[session_id])


class ZaloWebhookEvent(Base):
    """Minimal webhook receipt used for deduplication without storing message PII."""
    __tablename__ = "zalo_webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_key = Column(String(150), unique=True, nullable=False)
    event_name = Column(String(80), nullable=False)
    sender_hash = Column(String(64), nullable=True)
    payload_digest = Column(String(64), nullable=False)
    signature_valid = Column(Boolean, nullable=False)
    processing_status = Column(String(30), default="received", nullable=False)
    error = Column(Text, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
