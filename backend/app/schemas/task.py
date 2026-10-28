"""
Task Schemas - Request/Response models for task management
"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID
from app.models.task import TaskType, TaskDifficulty, TaskStatus, TaskScope, TaskCreatorType
from app.models.user import MemberLevel


# ============================================
# Task Schemas
# ============================================

class TaskCreate(BaseModel):
    """Schema for creating a new task (Admin only)"""
    title: str = Field(..., min_length=1, max_length=255)
    description: str
    type: TaskType
    scope: TaskScope = TaskScope.MANDATORY
    difficulty: TaskDifficulty = TaskDifficulty.MEDIUM
    min_level_required: int = 1
    max_participants: Optional[int] = None
    assignee_ids: List[str] = []
    prerequisite_task_ids: List[str] = []
    xp_reward: int = Field(..., ge=0)
    skill_tags: List[str] = []
    instructions: Optional[str] = None
    reference_links: List[str] = []
    deadline: Optional[datetime] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=1)
    creator_type: TaskCreatorType = TaskCreatorType.MANAGER
    target_member_level: MemberLevel = MemberLevel.NEW
    requires_manager_review: bool = True
    is_active: bool = True
    order_index: int = 0


class TaskUpdate(BaseModel):
    """Schema for updating a task (Admin only)"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    type: Optional[TaskType] = None
    scope: Optional[TaskScope] = None
    difficulty: Optional[TaskDifficulty] = None
    min_level_required: Optional[int] = None
    max_participants: Optional[int] = None
    assignee_ids: Optional[List[str]] = None
    prerequisite_task_ids: Optional[List[str]] = None
    xp_reward: Optional[int] = Field(None, ge=0)
    skill_tags: Optional[List[str]] = None
    instructions: Optional[str] = None
    reference_links: Optional[List[str]] = None
    deadline: Optional[datetime] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=1)
    creator_type: Optional[TaskCreatorType] = None
    target_member_level: Optional[MemberLevel] = None
    requires_manager_review: Optional[bool] = None
    is_active: Optional[bool] = None
    order_index: Optional[int] = None


class TaskResponse(BaseModel):
    """Public task information"""
    id: UUID
    title: str
    description: str
    type: TaskType
    scope: TaskScope
    difficulty: TaskDifficulty
    min_level_required: int
    max_participants: Optional[int]
    prerequisite_task_ids: List[str]
    xp_reward: int
    skill_tags: List[str]
    instructions: Optional[str]
    reference_links: List[str]
    deadline: Optional[datetime] = None
    estimated_duration_minutes: Optional[int] = None
    creator_type: TaskCreatorType = TaskCreatorType.MANAGER
    target_member_level: MemberLevel = MemberLevel.NEW
    requires_manager_review: bool = True
    is_active: bool
    order_index: int
    created_at: datetime
    updated_at: datetime
    creator_id: Optional[UUID]
    creator_name: Optional[str] = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Paginated task list"""
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int


# ============================================
# User Task Schemas
# ============================================

class UserTaskStart(BaseModel):
    """Schema for starting/claiming a task"""
    task_id: UUID


class UserTaskSubmit(BaseModel):
    """Schema for submitting a task for review"""
    proof_link: Optional[str] = Field(None, max_length=500)
    submission_notes: Optional[str] = None
    completion_percentage: float = Field(100.0, ge=0.0, le=100.0)
    evidence_links: List[str] = []

    model_config = {'extra': 'forbid'}


class UserTaskReview(BaseModel):
    """Schema for mentor to review a task"""
    status: TaskStatus = Field(..., description="approved or rejected")
    mentor_comment: Optional[str] = None
    manager_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    final_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    
    class Config:
        use_enum_values = True


class UserTaskProgressUpdate(BaseModel):
    """Schema for updating task progress before final submission."""
    progress_percentage: float = Field(..., ge=0.0, le=100.0)
    notes: Optional[str] = None


class UserTaskResponse(BaseModel):
    """User task progress information"""
    id: UUID
    user_id: UUID
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None
    task_id: UUID
    task: TaskResponse
    status: TaskStatus
    proof_link: Optional[str]
    submission_notes: Optional[str]
    submitted_at: Optional[datetime]
    reviewer_id: Optional[UUID]
    mentor_comment: Optional[str]
    reviewed_at: Optional[datetime]
    ai_score: Optional[float] = None
    ai_feedback: Optional[str] = None
    manager_score: Optional[float] = None
    final_score: Optional[float] = None
    final_feedback: Optional[str] = None
    needs_manager_review: bool = True
    xp_earned: int
    assigned_for_date: Optional[date] = None
    deadline_at: Optional[datetime] = None
    progress_percentage: float = 0.0
    completion_percentage: float = 0.0
    evidence_links: List[str] = []
    assigned_by_id: Optional[UUID] = None
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserTaskListResponse(BaseModel):
    """List of user tasks with status"""
    tasks: List[UserTaskResponse]
    total: int
    completed_count: int
    pending_count: int
    in_progress_count: int


class TaskStatsResponse(BaseModel):
    """Statistics for tasks"""
    total_tasks: int
    core_tasks: int
    bounty_tasks: int
    active_tasks: int
    total_xp_available: int


class TaskParticipant(BaseModel):
    """Task participant information"""
    id: UUID
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    role: str
    level: int
    current_xp: int
    task_status: TaskStatus
    started_at: Optional[datetime]
    submitted_at: Optional[datetime]
    completed_at: Optional[datetime]
    proof_link: Optional[str]
    mentor_comment: Optional[str]
    ai_score: Optional[float] = None
    manager_score: Optional[float] = None
    final_score: Optional[float] = None
    progress_percentage: float = 0.0
    completion_percentage: float = 0.0
    assigned_for_date: Optional[date] = None
    deadline_at: Optional[datetime] = None
    xp_earned: int

    class Config:
        from_attributes = True


class TaskDetailResponse(BaseModel):
    """Detailed task information with participants"""
    id: UUID
    title: str
    description: str
    type: TaskType
    scope: TaskScope
    difficulty: TaskDifficulty
    min_level_required: int
    xp_reward: int
    skill_tags: List[str]
    deadline: Optional[datetime] = None
    estimated_duration_minutes: Optional[int] = None
    creator_type: TaskCreatorType = TaskCreatorType.MANAGER
    target_member_level: MemberLevel = MemberLevel.NEW
    requires_manager_review: bool = True
    is_active: bool
    max_participants: Optional[int]
    assignee_ids: List[str]
    created_at: datetime
    updated_at: datetime
    # Statistics
    total_participants: int
    in_progress_count: int
    submitted_count: int
    completed_count: int
    rejected_count: int
    # Participants list
    participants: List[TaskParticipant]

    class Config:
        from_attributes = True
