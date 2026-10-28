"""
Schedule Schemas - Request/Response models
"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID
from app.models.schedule import Shift, AttendanceStatus


# ============================================
# Schedule Schemas
# ============================================

class ScheduleCreate(BaseModel):
    """Schema for creating a schedule registration"""
    work_date: date
    shift: Shift
    
    class Config:
        use_enum_values = True


class ScheduleUpdate(BaseModel):
    """Schema for updating a schedule"""
    is_cancelled: bool = True
    cancel_reason: Optional[str] = None


class ScheduleResponse(BaseModel):
    """Schedule information"""
    id: UUID
    user_id: UUID
    work_date: date
    shift: Shift
    registration_type: str = "manual"
    registered_at: datetime
    is_cancelled: bool
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        use_enum_values = True


class ClassScheduleResponse(BaseModel):
    """Class schedule information"""
    id: UUID
    subject_name: str
    room: Optional[str] = None
    start_datetime: datetime
    end_datetime: datetime
    is_cancelled: bool
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    """Paginated schedule list"""
    schedules: List[ScheduleResponse]
    total: int


class WeekScheduleRequest(BaseModel):
    """Batch create schedules for a week"""
    schedules: List[ScheduleCreate]


# ============================================
# Attendance Schemas
# ============================================

class AttendanceCheckIn(BaseModel):
    """Check-in request"""
    shift: Shift
    notes: Optional[str] = None
    
    class Config:
        use_enum_values = True


class AttendanceCheckOut(BaseModel):
    """Check-out request"""
    notes: Optional[str] = None


class AttendanceResponse(BaseModel):
    """Attendance information"""
    id: UUID
    user_id: UUID
    schedule_id: Optional[UUID] = None
    work_date: date
    shift: Optional[Shift] = None
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    status: AttendanceStatus
    discipline_points_change: int
    bonus_points: int
    notes: Optional[str] = None
    auto_reconciled: bool
    reconciled_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        use_enum_values = True


class AttendanceListResponse(BaseModel):
    """Paginated attendance list"""
    attendances: List[AttendanceResponse]
    total: int


class AttendanceStatsResponse(BaseModel):
    """Attendance statistics"""
    total_scheduled: int
    total_attended: int
    total_absent: int
    total_late: int
    total_extra: int
    attendance_rate: float  # Percentage
    discipline_points_total: int
    bonus_points_total: int


class WeekScheduleResponse(BaseModel):
    """Week overview"""
    week_start: date
    week_end: date
    schedules: List[ScheduleResponse]
    class_schedules: List[ClassScheduleResponse] = []
    attendances: List[AttendanceResponse] = []
    stats: Optional[AttendanceStatsResponse] = None
