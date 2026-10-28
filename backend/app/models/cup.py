"""Weekly cup competition models."""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class WeeklyCupEventStatus(str, Enum):
    """Lifecycle for a weekly cup event."""
    SCHEDULED = "scheduled"
    OPEN = "open"
    CLOSED = "closed"
    AWARDED = "awarded"


class CupDefinition(Base):
    """Fixed catalog of the 8 unique cups."""
    __tablename__ = "cup_definitions"
    __table_args__ = (
        UniqueConstraint("code", name="uq_cup_definitions_code"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(80), nullable=False)
    title = Column(String(120), nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String(20), default="CUP", nullable=False)
    color = Column(String(20), default="#f59e0b", nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    events = relationship("WeeklyCupEvent", back_populates="cup")
    user_cups = relationship("UserCup", back_populates="cup", cascade="all, delete-orphan")


class WeeklyCupEvent(Base):
    """A weekly Friday competition for one unique cup."""
    __tablename__ = "weekly_cup_events"
    __table_args__ = (
        UniqueConstraint("week_start", name="uq_weekly_cup_events_week_start"),
        UniqueConstraint("cup_id", name="uq_weekly_cup_events_cup_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cup_id = Column(UUID(as_uuid=True), ForeignKey("cup_definitions.id", ondelete="RESTRICT"), nullable=False)
    week_start = Column(Date, nullable=False)
    opens_at = Column(DateTime, nullable=False)
    closes_at = Column(DateTime, nullable=False)
    status = Column(String(30), default=WeeklyCupEventStatus.OPEN.value, nullable=False)
    winner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    winner_score = Column(Float, nullable=True)
    awarded_at = Column(DateTime, nullable=True)
    questions = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    cup = relationship("CupDefinition", back_populates="events")
    winner = relationship("User", foreign_keys=[winner_user_id])
    awards = relationship("UserCup", back_populates="event", cascade="all, delete-orphan")
    attempts = relationship("WeeklyCupAttempt", back_populates="event", cascade="all, delete-orphan")


class UserCup(Base):
    """A unique cup awarded to a user."""
    __tablename__ = "user_cups"
    __table_args__ = (
        UniqueConstraint("cup_id", name="uq_user_cups_cup_id"),
        UniqueConstraint("event_id", name="uq_user_cups_event_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    cup_id = Column(UUID(as_uuid=True), ForeignKey("cup_definitions.id", ondelete="RESTRICT"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("weekly_cup_events.id", ondelete="CASCADE"), nullable=False)
    rank = Column(Integer, default=1, nullable=False)
    score_snapshot = Column(Float, default=0.0, nullable=False)
    discipline_score_snapshot = Column(Float, default=0.0, nullable=False)
    awarded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id], backref="cups")
    cup = relationship("CupDefinition", back_populates="user_cups")
    event = relationship("WeeklyCupEvent", back_populates="awards")


class WeeklyCupAttempt(Base):
    """One timed multiple-choice test attempt for a weekly cup event."""
    __tablename__ = "weekly_cup_attempts"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_weekly_cup_attempts_event_user"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("weekly_cup_events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    answers = Column(JSON, default=dict, nullable=False)
    score = Column(Integer, nullable=True)
    total_questions = Column(Integer, default=20, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    event = relationship("WeeklyCupEvent", back_populates="attempts")
    user = relationship("User", foreign_keys=[user_id], backref="weekly_cup_attempts")
