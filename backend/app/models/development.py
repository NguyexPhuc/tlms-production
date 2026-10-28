"""
Member development models for TLMS.

These models extend the existing task, XP, discipline, and RBAC system without
replacing the current authentication or role model.
"""
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
from app.models.task import TaskCreatorType, TaskDifficulty
from app.models.user import MemberLevel


class DailyTaskStatus(str, Enum):
    """Task-based attendance status for a member on a specific day."""
    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSED = "missed"


class QuestionStatus(str, Enum):
    """Question lifecycle status."""
    ACTIVE = "active"
    ARCHIVED = "archived"


class QuestionAnswerStatus(str, Enum):
    """Question answer review status."""
    NOT_STARTED = "not_started"
    SUBMITTED = "submitted"
    AI_REVIEWED = "ai_reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


class PromotionStatus(str, Enum):
    """Promotion review workflow status."""
    ELIGIBLE = "eligible"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class NotificationChannel(str, Enum):
    """Delivery channel. Only in-app is implemented now."""
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


class TaskProgressUpdate(Base):
    """Immutable history of progress updates for a UserTask."""
    __tablename__ = "task_progress_updates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_task_id = Column(UUID(as_uuid=True), ForeignKey("user_tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    progress_percentage = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user_task = relationship("UserTask", backref="progress_updates")
    user = relationship("User", backref="task_progress_updates")


class DailyTaskReport(Base):
    """Daily task completion summary used for task-based attendance."""
    __tablename__ = "daily_task_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "report_date", name="uq_daily_task_reports_user_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    report_date = Column(Date, nullable=False)
    assigned_count = Column(Integer, default=0, nullable=False)
    completed_count = Column(Integer, default=0, nullable=False)
    late_count = Column(Integer, default=0, nullable=False)
    missed_count = Column(Integer, default=0, nullable=False)
    completion_rate = Column(Float, default=0.0, nullable=False)
    attendance_status = Column(
        SQLEnum(DailyTaskStatus, values_callable=lambda x: [e.value for e in x]),
        default=DailyTaskStatus.MISSED,
        nullable=False,
    )
    discipline_delta = Column(Float, default=0.0, nullable=False)
    reliability_delta = Column(Float, default=0.0, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    recalculated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", backref="daily_task_reports")


class MemberRoadmap(Base):
    """Personal 8-week development roadmap for a candidate/member."""
    __tablename__ = "member_roadmaps"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_member_roadmaps_user_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(30), default="active", nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    target_end_at = Column(DateTime, nullable=False)
    current_week = Column(Integer, default=1, nullable=False)
    current_day = Column(Integer, default=1, nullable=False)
    total_weeks = Column(Integer, default=8, nullable=False)
    total_days = Column(Integer, default=56, nullable=False)
    progress_percentage = Column(Float, default=12.5, nullable=False)
    current_stage = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", backref="member_roadmaps")
    weeks = relationship(
        "MemberRoadmapWeek",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="MemberRoadmapWeek.week_number",
    )


class MemberRoadmapWeek(Base):
    """A weekly milestone inside the personal 8-week roadmap."""
    __tablename__ = "member_roadmap_weeks"
    __table_args__ = (
        UniqueConstraint("roadmap_id", "week_number", name="uq_member_roadmap_weeks_roadmap_week"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    roadmap_id = Column(UUID(as_uuid=True), ForeignKey("member_roadmaps.id", ondelete="CASCADE"), nullable=False)
    week_number = Column(Integer, nullable=False)
    title = Column(String(160), nullable=False)
    stage = Column(String(120), nullable=False)
    goals = Column(JSON, default=list, nullable=False)
    question_focus = Column(Text, nullable=False)
    daily_task_focus = Column(Text, nullable=False)
    quest_focus = Column(Text, nullable=False)
    skill_targets = Column(JSON, default=list, nullable=False)
    progress_percentage = Column(Float, default=0.0, nullable=False)
    weekly_evaluation = Column(Text, nullable=True)
    planned_start_at = Column(DateTime, nullable=False)
    planned_end_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    roadmap = relationship("MemberRoadmap", back_populates="weeks")


class MemberSkillProfile(Base):
    """Per-skill learner profile used by the adaptive question flow."""
    __tablename__ = "member_skill_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_key", name="uq_member_skill_profiles_user_skill"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    skill_key = Column(String(80), nullable=False)
    mastery_score = Column(Float, default=50.0, nullable=False)
    confidence = Column(Float, default=0.3, nullable=False)
    current_difficulty = Column(Float, default=3.0, nullable=False)
    attempts_count = Column(Integer, default=0, nullable=False)
    correct_count = Column(Integer, default=0, nullable=False)
    last_score = Column(Float, nullable=True)
    weak_topics = Column(JSON, default=list, nullable=False)
    strong_topics = Column(JSON, default=list, nullable=False)
    last_evaluated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id], backref="skill_profiles")


class AchievementBadge(Base):
    """System achievement milestone and badge catalog."""
    __tablename__ = "achievement_badges"
    __table_args__ = (
        UniqueConstraint("code", name="uq_achievement_badges_code"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(80), nullable=False)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(60), nullable=False)
    metric = Column(String(80), nullable=False)
    target_value = Column(Float, nullable=False)
    badge_icon = Column(String(20), default="XP", nullable=False)
    badge_color = Column(String(20), default="#1E90FF", nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user_badges = relationship("UserAchievementBadge", back_populates="badge", cascade="all, delete-orphan")


class UserAchievementBadge(Base):
    """A badge unlocked by a user."""
    __tablename__ = "user_achievement_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="uq_user_achievement_badges_user_badge"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    badge_id = Column(UUID(as_uuid=True), ForeignKey("achievement_badges.id", ondelete="CASCADE"), nullable=False)
    progress_value = Column(Float, default=0.0, nullable=False)
    unlocked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id], backref="achievement_badges")
    badge = relationship("AchievementBadge", back_populates="user_badges")


class Question(Base):
    """Question template for member development."""
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    question = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    difficulty = Column(
        SQLEnum(TaskDifficulty, values_callable=lambda x: [e.value for e in x]),
        default=TaskDifficulty.MEDIUM,
        nullable=False,
    )
    category = Column(String(100), nullable=True)
    topic = Column(String(120), nullable=True)
    skill_key = Column(String(80), nullable=True)
    question_type = Column(String(40), default="short_answer", nullable=False)
    numeric_difficulty = Column(Float, default=3.0, nullable=False)
    source = Column(String(40), default="manager", nullable=False)
    learning_objective = Column(Text, nullable=True)
    is_baseline = Column(Boolean, default=False, nullable=False)
    points = Column(Integer, default=0, nullable=False)
    expected_duration_minutes = Column(Integer, nullable=True)
    target_member_level = Column(
        SQLEnum(MemberLevel, values_callable=lambda x: [e.value for e in x]),
        default=MemberLevel.NEW,
        nullable=False,
    )
    creator_type = Column(
        SQLEnum(TaskCreatorType, values_callable=lambda x: [e.value for e in x]),
        default=TaskCreatorType.MANAGER,
        nullable=False,
    )
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expected_answer = Column(Text, nullable=True)
    accepted_concepts = Column(JSON, nullable=True)
    options = Column(JSON, nullable=True)
    correct_option = Column(String(1), nullable=True)
    correct_options = Column(JSON, nullable=True)
    feedback = Column(Text, nullable=True)
    status = Column(
        SQLEnum(QuestionStatus, values_callable=lambda x: [e.value for e in x]),
        default=QuestionStatus.ACTIVE,
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_id], backref="created_questions")


class UserQuestionAnswer(Base):
    """A member's submitted answer for a question."""
    __tablename__ = "user_question_answers"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_user_question_answers_user_question"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    answer = Column(Text, nullable=False)
    ai_score = Column(Float, nullable=True)
    ai_feedback = Column(Text, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    ai_breakdown = Column(JSON, nullable=True)
    manager_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    points_awarded = Column(Integer, default=0, nullable=False)
    feedback = Column(Text, nullable=True)
    status = Column(
        SQLEnum(QuestionAnswerStatus, values_callable=lambda x: [e.value for e in x]),
        default=QuestionAnswerStatus.SUBMITTED,
        nullable=False,
    )
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id], backref="question_answers")
    question = relationship("Question", backref="answers")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])


class Notification(Base):
    """In-app notification history."""
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(80), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(
        SQLEnum(NotificationChannel, values_callable=lambda x: [e.value for e in x]),
        default=NotificationChannel.IN_APP,
        nullable=False,
    )
    payload = Column(JSON, nullable=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id], backref="notifications")
    actor = relationship("User", foreign_keys=[actor_id])

    @property
    def is_read(self) -> bool:
        return self.read_at is not None


class PromotionReview(Base):
    """Promotion eligibility and manager decision history."""
    __tablename__ = "promotion_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    from_member_level = Column(
        SQLEnum(MemberLevel, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    to_member_level = Column(
        SQLEnum(MemberLevel, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status = Column(
        SQLEnum(PromotionStatus, values_callable=lambda x: [e.value for e in x]),
        default=PromotionStatus.ELIGIBLE,
        nullable=False,
    )
    metrics = Column(JSON, nullable=True)
    manager_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    manager_notes = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id], backref="promotion_reviews")
    manager = relationship("User", foreign_keys=[manager_id])


class MemberEvaluation(Base):
    """Persisted score snapshot for member development."""
    __tablename__ = "member_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_completion_rate = Column(Float, default=0.0, nullable=False)
    task_quality_score = Column(Float, default=0.0, nullable=False)
    attendance_score = Column(Float, default=0.0, nullable=False)
    discipline_score = Column(Float, default=100.0, nullable=False)
    activity_score = Column(Float, default=0.0, nullable=False)
    manager_score = Column(Float, nullable=True)
    final_score = Column(Float, default=0.0, nullable=False)
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id], backref="member_evaluations")
    created_by = relationship("User", foreign_keys=[created_by_id])
