"""
Profile Schemas for TLMS
Pydantic schemas for profile-related API requests and responses
"""
from datetime import datetime, date
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl

from app.models.profile import EvidenceStatus


# ============================================
# Profile Evidence Schemas
# ============================================

class ProfileEvidenceBase(BaseModel):
    """Base schema for profile evidence"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    evidence_links: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    task_id: Optional[UUID] = None
    is_public: bool = True


class ProfileEvidenceCreate(ProfileEvidenceBase):
    """Schema for creating new evidence"""
    pass


class ProfileEvidenceUpdate(BaseModel):
    """Schema for updating evidence"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    evidence_links: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None


class ProfileEvidenceVerify(BaseModel):
    """Schema for verifying evidence (Mentor/Admin only)"""
    status: EvidenceStatus
    verification_notes: Optional[str] = None
    is_featured: bool = False


class ProfileEvidenceOut(ProfileEvidenceBase):
    """Schema for evidence output"""
    id: UUID
    user_id: UUID
    status: EvidenceStatus
    is_featured: bool
    verified_by_id: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# Profile Statistics Schemas
# ============================================

class WorkScheduleStats(BaseModel):
    """Work schedule statistics"""
    total_hours_this_week: float = 0.0
    total_hours_this_month: float = 0.0
    total_hours_all_time: float = 0.0
    attendance_rate: float = 100.0  # Percentage
    total_days_worked: int = 0


class TaskStats(BaseModel):
    """Task completion statistics"""
    total_tasks_completed: int = 0
    core_tasks_completed: int = 0
    bounty_tasks_completed: int = 0
    total_xp_earned: int = 0
    current_level: int = 1
    current_xp: int = 0
    core_task_progress: float = 0.0  # Percentage


class AchievementSummary(BaseModel):
    """Achievement and rewards summary"""
    total_evidence: int = 0
    verified_evidence: int = 0
    featured_evidence: int = 0
    skill_tags: List[str] = Field(default_factory=list)
    discipline_score: float = 100.0
    is_ready_to_promote: bool = False


class ProfileStats(BaseModel):
    """Complete profile statistics"""
    work_schedule: WorkScheduleStats
    tasks: TaskStats
    achievements: AchievementSummary


# ============================================
# Auto-Schedule Schemas
# ============================================

class AutoScheduleRequest(BaseModel):
    """Request to auto-register work schedule based on class schedule"""
    week_start_date: date
    target_hours_per_day: float = Field(default=8.0, ge=0, le=24)
    prefer_morning: bool = False
    prefer_afternoon: bool = False


class ScheduleConflict(BaseModel):
    """Schedule conflict information"""
    date: date
    shift: str
    reason: str


class AutoScheduleResult(BaseModel):
    """Result of auto-schedule operation"""
    success: bool
    message: str
    schedules_created: int = 0
    conflicts: List[ScheduleConflict] = Field(default_factory=list)


# ============================================
# Complete Profile Response
# ============================================

class UserBasicInfo(BaseModel):
    """Basic user info for profile"""
    id: UUID
    email: str
    student_id: Optional[str] = None
    full_name: str
    roles: List[str]
    primary_role: str
    
    class Config:
        from_attributes = True


class ProfileResponse(BaseModel):
    """Complete user profile response"""
    user: UserBasicInfo
    stats: ProfileStats
    evidence: List[ProfileEvidenceOut]
    recent_tasks: List[dict]  # Recent task submissions
    upcoming_schedules: List[dict]  # Upcoming work schedules
