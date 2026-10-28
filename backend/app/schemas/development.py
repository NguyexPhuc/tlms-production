"""Schemas for member development dashboards and workflows."""
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.development import DailyTaskStatus, PromotionStatus
from app.models.user import MemberLevel
from app.schemas.notification import NotificationResponse
from app.schemas.task import UserTaskResponse


class DailyTaskAssignRequest(BaseModel):
    target_date: Optional[date] = None
    target_member_level: MemberLevel = MemberLevel.NEW
    user_ids: Optional[List[UUID]] = None
    task_ids: Optional[List[UUID]] = None
    tasks_per_member: int = Field(5, ge=1, le=20)
    deadline_at: Optional[datetime] = None
    include_ai_tasks: bool = True


class DailyTaskAssignResponse(BaseModel):
    target_date: date
    target_member_level: MemberLevel
    users_considered: int
    tasks_considered: int
    assignments_created: int
    skipped_existing: int
    skipped_official_ai: int

    class Config:
        use_enum_values = True


class DailyTaskReportResponse(BaseModel):
    id: UUID
    user_id: UUID
    report_date: date
    assigned_count: int
    completed_count: int
    late_count: int
    missed_count: int
    completion_rate: float
    attendance_status: DailyTaskStatus
    discipline_delta: float
    reliability_delta: float
    generated_at: datetime
    recalculated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True


class DailyTaskReconcileRequest(BaseModel):
    target_date: Optional[date] = None
    user_ids: Optional[List[UUID]] = None


class DailyTaskReconcileResponse(BaseModel):
    target_date: date
    processed_count: int
    reports: List[DailyTaskReportResponse]


class RoadmapWeekResponse(BaseModel):
    id: UUID
    week_number: int
    title: str
    stage: str
    goals: List[str] = Field(default_factory=list)
    question_focus: str
    daily_task_focus: str
    quest_focus: str
    skill_targets: List[str] = Field(default_factory=list)
    progress_percentage: float
    weekly_evaluation: Optional[str] = None
    planned_start_at: datetime
    planned_end_at: datetime
    is_current: bool = False
    is_completed: bool = False


class MemberRoadmapResponse(BaseModel):
    id: UUID
    user_id: UUID
    status: str
    started_at: datetime
    target_end_at: datetime
    current_week: int
    current_day: int
    total_weeks: int
    total_days: int
    progress_percentage: float
    current_stage: str
    weeks: List[RoadmapWeekResponse] = Field(default_factory=list)


class AchievementBadgeProgress(BaseModel):
    id: UUID
    code: str
    title: str
    description: str
    category: str
    metric: str
    target_value: float
    current_value: float
    progress_percentage: float
    is_unlocked: bool
    unlocked_at: Optional[datetime] = None
    badge_icon: str
    badge_color: str
    sort_order: int


class AchievementDashboard(BaseModel):
    total_count: int
    unlocked_count: int
    overall_progress: float
    featured: List[AchievementBadgeProgress] = Field(default_factory=list)
    next_milestones: List[AchievementBadgeProgress] = Field(default_factory=list)
    badges: List[AchievementBadgeProgress] = Field(default_factory=list)


class MemberDevelopmentDashboard(BaseModel):
    member_level: MemberLevel
    current_xp: int
    level: int
    discipline_score: float
    reliability_score: float
    member_score: float
    promotion_progress: float
    today_tasks: List[UserTaskResponse]
    assigned_tasks: List[UserTaskResponse] = Field(default_factory=list)
    completed_tasks: int
    pending_tasks: int
    daily_completion_rate: float
    attendance_status: Optional[DailyTaskStatus] = None
    promotion_eligible: bool
    unread_notifications: int
    notifications: List[NotificationResponse]
    roadmap: Optional[MemberRoadmapResponse] = None
    achievements: AchievementDashboard

    class Config:
        use_enum_values = True


class ManagerDevelopmentSummary(BaseModel):
    total_members: int
    new_members: int
    diligent_members: int
    official_members: int
    daily_task_completion: float
    missed_tasks: int
    pending_reviews: int
    promotion_eligible: int
    average_completion_rate: float
    active_members: int


class PromotionReviewResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None
    from_member_level: MemberLevel
    to_member_level: MemberLevel
    status: PromotionStatus
    metrics: Optional[Dict[str, Any]] = None
    manager_id: Optional[UUID] = None
    manager_notes: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True


class PromotionDecisionRequest(BaseModel):
    manager_notes: Optional[str] = None


class MemberEvaluationResponse(BaseModel):
    id: UUID
    user_id: UUID
    task_completion_rate: float
    task_quality_score: float
    attendance_score: float
    discipline_score: float
    activity_score: float
    manager_score: Optional[float] = None
    final_score: float
    notes: Optional[str] = None
    created_by_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True
