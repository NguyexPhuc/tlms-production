"""Daily Quest models."""
import uuid
from datetime import datetime
from enum import Enum

import pytz
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


VN_TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")


def vietnam_now_naive() -> datetime:
    """Return local Vietnam time as a naive datetime for timestamp columns."""
    return datetime.now(VN_TIMEZONE).replace(tzinfo=None)


class DailyQuestDifficulty(str, Enum):
    """Daily Quest difficulty shown to candidates."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class DailyQuestStatus(str, Enum):
    """Daily Quest lifecycle status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    AI_REVIEWED = "ai_reviewed"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DailyQuestType(str, Enum):
    """Quest category."""
    DAILY = "daily"
    LIMIT = "limit"


class DailyQuest(Base):
    """A generated daily quest assigned to one candidate/member."""
    __tablename__ = "daily_quests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    quest_type = Column(
        SQLEnum(DailyQuestType, values_callable=lambda x: [e.value for e in x]),
        default=DailyQuestType.DAILY,
        nullable=False,
    )
    difficulty = Column(
        SQLEnum(DailyQuestDifficulty, values_callable=lambda x: [e.value for e in x]),
        default=DailyQuestDifficulty.EASY,
        nullable=False,
    )
    xp_reward = Column(Integer, default=10, nullable=False)
    status = Column(
        SQLEnum(DailyQuestStatus, values_callable=lambda x: [e.value for e in x]),
        default=DailyQuestStatus.PENDING,
        nullable=False,
    )
    created_at = Column(DateTime, default=vietnam_now_naive, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    proof_text = Column(Text, nullable=True)
    proof_link = Column(String(500), nullable=True)
    proof_image_url = Column(String(500), nullable=True)
    proof_image_name = Column(String(255), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    ai_score = Column(Float, nullable=True)
    ai_feedback = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    requires_image_proof = Column(Boolean, default=False, nullable=False)
    auto_pass_score = Column(Integer, default=70, nullable=False)

    user = relationship("User", foreign_keys=[user_id], backref="daily_quests")
    created_by = relationship("User", foreign_keys=[created_by_id])


class QuestLimitConfig(Base):
    """Configurable daily quest limit by role and level range."""
    __tablename__ = "quest_limit_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role = Column(String(50), nullable=True)
    min_level = Column(Integer, default=1, nullable=False)
    max_level = Column(Integer, nullable=True)
    quest_limit = Column(Integer, default=5, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=vietnam_now_naive, nullable=False)
    updated_at = Column(DateTime, default=vietnam_now_naive, onupdate=vietnam_now_naive, nullable=False)
