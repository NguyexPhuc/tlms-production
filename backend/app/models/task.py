"""
Task Models for TLMS
- Core Tasks: Onboarding, mandatory tasks
- Bounty Tasks: Challenge tasks, projects
"""
import uuid
from datetime import date, datetime
from enum import Enum
from sqlalchemy import Column, Date, String, DateTime, Integer, Float, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.user import MemberLevel


class TaskType(str, Enum):
    """Task types"""
    CORE = "core"  # Mandatory onboarding/culture tasks
    BOUNTY = "bounty"  # Challenge/project tasks


class TaskDifficulty(str, Enum):
    """Task difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    ADVANCED = "advanced"
    EXPERT = "expert"


class TaskScope(str, Enum):
    """Task visibility and assignment scope"""
    MANDATORY = "mandatory"     # Type 1: Assigned to all relevant users, no accept needed
    OPT_IN = "opt_in"           # Type 2: Limited quantity, requires acceptance
    PRIVATE = "private"         # Type 3: Assignee only



class TaskStatus(str, Enum):
    """User task submission status"""
    LOCKED = "locked"  # Not available yet (prerequisite not met)
    AVAILABLE = "available"  # Can be started
    IN_PROGRESS = "in_progress"  # User claimed/started
    SUBMITTED = "submitted"  # Waiting for review
    AI_REVIEWED = "ai_reviewed"  # AI has produced a suggestion, waiting for manager/mentor
    APPROVED = "approved"  # Mentor approved
    REJECTED = "rejected"  # Mentor rejected
    LATE = "late"  # Submitted after deadline or past due
    MISSED = "missed"  # Deadline passed without submission
    COMPLETED = "completed"  # Final completed state


class TaskCreatorType(str, Enum):
    """Who created/suggested the task."""
    AI = "ai"
    MANAGER = "manager"
    SYSTEM = "system"


class Task(Base):
    """
    Task template/definition
    Admin creates these tasks for users to complete
    """
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic Info
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    type = Column(
        SQLEnum(TaskType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    scope = Column(
        SQLEnum(TaskScope, values_callable=lambda x: [e.value for e in x]),
        default=TaskScope.MANDATORY,
        nullable=False
    )
    difficulty = Column(
        SQLEnum(TaskDifficulty, values_callable=lambda x: [e.value for e in x]),
        default=TaskDifficulty.MEDIUM,
        nullable=False
    )
    
    # Scope Settings
    max_participants = Column(Integer, nullable=True)  # For OPT_IN
    assignee_ids = Column(ARRAY(String(36)), default=[], nullable=False)  # For PRIVATE

    # Requirements
    min_level_required = Column(Integer, default=1, nullable=False)
    prerequisite_task_ids = Column(
        ARRAY(String(36)),  # Array of task IDs that must be completed first
        default=[],
        nullable=False
    )
    
    # Rewards
    xp_reward = Column(Integer, default=0, nullable=False)  # XP gained on completion
    skill_tags = Column(
        ARRAY(String(50)),  # e.g., ['web-dev', 'database', 'docker']
        default=[],
        nullable=False
    )
    
    # Content
    instructions = Column(Text, nullable=True)  # Detailed instructions
    reference_links = Column(ARRAY(String(500)), default=[], nullable=False)

    # Creator info (who created this task)
    creator_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    creator = relationship("User", foreign_keys=[creator_id])
    creator_type = Column(
        SQLEnum(TaskCreatorType, values_callable=lambda x: [e.value for e in x]),
        default=TaskCreatorType.MANAGER,
        nullable=False
    )
    target_member_level = Column(
        SQLEnum(MemberLevel, values_callable=lambda x: [e.value for e in x]),
        default=MemberLevel.NEW,
        nullable=False
    )

    # Development tracking
    deadline = Column(DateTime, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    requires_manager_review = Column(Boolean, default=True, nullable=False)

    # Settings
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)  # Display order
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user_tasks = relationship("UserTask", back_populates="task", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Task {self.title} ({self.type.value})>"

    @property
    def creator_name(self) -> str | None:
        if not self.creator:
            return None
        return self.creator.full_name or self.creator.email


class UserTask(Base):
    """
    User's progress on a specific task
    This is the transaction table tracking user's work
    """
    __tablename__ = "user_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    
    # Status
    status = Column(
        SQLEnum(TaskStatus, values_callable=lambda x: [e.value for e in x]),
        default=TaskStatus.AVAILABLE,
        nullable=False
    )
    
    # Submission
    proof_link = Column(String(500), nullable=True)  # Github link, Drive link, etc.
    submission_notes = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    
    # Review
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    mentor_comment = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    ai_score = Column(Float, nullable=True)
    ai_feedback = Column(Text, nullable=True)
    manager_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    final_feedback = Column(Text, nullable=True)
    needs_manager_review = Column(Boolean, default=True, nullable=False)
    
    # XP (stored here for history tracking)
    xp_earned = Column(Integer, default=0, nullable=False)

    # Assignment and progress
    assigned_for_date = Column(Date, nullable=True)
    deadline_at = Column(DateTime, nullable=True)
    progress_percentage = Column(Float, default=0.0, nullable=False)
    completion_percentage = Column(Float, default=0.0, nullable=False)
    evidence_links = Column(ARRAY(String(500)), default=[], nullable=False)
    assigned_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)  # When user claimed the task
    completed_at = Column(DateTime, nullable=True)  # When finally approved
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="user_tasks")
    user = relationship("User", foreign_keys=[user_id], backref="user_tasks")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])
    
    def __repr__(self):
        return f"<UserTask user={self.user_id} task={self.task_id} status={self.status.value}>"
