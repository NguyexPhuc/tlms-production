"""
Schedule and Attendance Models for TLMS
- Weekly schedule registration
- Check-in/Check-out tracking
- Attendance reconciliation
"""
import uuid
from datetime import datetime, date, time
from enum import Enum
from sqlalchemy import Column, String, DateTime, Date, Time, Boolean, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Shift(str, Enum):
    """Work shift types"""
    MORNING = "morning"    # Sáng: 7:30 - 11:30
    AFTERNOON = "afternoon"  # Chiều: 13:00 - 17:00
    EVENING = "evening"    # Tối: 18:00 - 22:00


class RegistrationType(str, Enum):
    """How the schedule was created"""
    MANUAL = "manual"
    AUTO = "auto"


class AttendanceStatus(str, Enum):
    """Attendance status after reconciliation"""
    PENDING = "pending"        # Chưa đến giờ làm việc
    PRESENT = "present"        # Đúng lịch + Có mặt
    ABSENT = "absent"          # Đúng lịch + Vắng mặt
    LATE = "late"              # Đến muộn
    EARLY_LEAVE = "early_leave"  # Về sớm
    EXTRA = "extra"            # Không đăng ký nhưng có mặt (overtime/extra effort)


class Schedule(Base):
    """
    Weekly schedule registration
    Users register their work slots for the week
    """
    __tablename__ = "schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Schedule details
    work_date = Column(Date, nullable=False)  # Ngày làm việc
    shift = Column(String(20), nullable=False)
    
    # Registration info
    registration_type = Column(
        SQLEnum(RegistrationType, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=RegistrationType.MANUAL,
        nullable=False
    )
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Status tracking
    is_cancelled = Column(Boolean, default=False, nullable=False)
    cancelled_at = Column(DateTime, nullable=True)
    cancel_reason = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="schedules")
    attendance = relationship("Attendance", back_populates="schedule", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Schedule user={self.user_id} date={self.work_date} shift={self.shift.value}>"


class Attendance(Base):
    """
    Attendance tracking and reconciliation
    Records actual check-in/check-out and compares with schedule
    """
    __tablename__ = "attendances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("schedules.id", ondelete="SET NULL"), nullable=True)
    
    # Attendance details
    work_date = Column(Date, nullable=False)
    shift = Column(
        SQLEnum(Shift, values_callable=lambda x: [e.value for e in x], native_enum=False),
        nullable=True  # Nullable because user might check-in without registration
    )
    
    # Check-in/Check-out times
    check_in_time = Column(DateTime, nullable=True)
    check_out_time = Column(DateTime, nullable=True)
    
    # Reconciliation result
    status = Column(
        SQLEnum(AttendanceStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=AttendanceStatus.PENDING,
        nullable=False
    )
    
    # Points tracking (from reconciliation)
    discipline_points_change = Column(Integer, default=0, nullable=False)  # Can be negative
    bonus_points = Column(Integer, default=0, nullable=False)  # Extra effort bonus
    
    # Notes
    notes = Column(String(500), nullable=True)
    auto_reconciled = Column(Boolean, default=False, nullable=False)  # True if reconciled by system
    reconciled_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="attendances")
    schedule = relationship("Schedule", back_populates="attendance")
    
    def __repr__(self):
        return f"<Attendance user={self.user_id} date={self.work_date} status={self.status.value}>"


class ClassSchedule(Base):
    """
    Imported class schedule from LHU API
    Used to calculate busy slots
    """
    __tablename__ = "class_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    subject_name = Column(String(255), nullable=False)
    room = Column(String(50), nullable=True)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    
    is_cancelled = Column(Boolean, default=False, nullable=False) # LHU cancelled
    description = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    user = relationship("User", backref="class_schedules")
    
    def __repr__(self):
        return f"<ClassSchedule user={self.user_id} subject={self.subject_name} date={self.start_datetime}>"
