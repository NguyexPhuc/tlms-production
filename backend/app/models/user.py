"""
User Model for TLMS
Following the database schema from oauth.md document
S4H-linked users do not need a local password. Standalone TLMS accounts may
store an optional salted password hash for continuity during S4H outages.
"""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Integer, Float, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app.core.database import Base


class UserRole(str, Enum):
    """
    RBAC Roles as defined in system.md
    - Candidate: Limited access (view roadmap, receive tasks, register schedule)
    - Member: Access internal resources, document library
    - Mentor: Approve/Reject, Review, view mentee progress reports
    - Admin: Highest administrative rights (System Configuration)
    """
    CANDIDATE = "candidate"
    MEMBER = "member"
    MENTOR = "mentor"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"


class MemberLevel(str, Enum):
    """
    Member development status.
    This is intentionally separate from UserRole, which is used for RBAC.
    """
    NEW = "new"
    DILIGENT = "diligent"
    OFFICIAL = "official"


class User(Base):
    """
    Local User table (local_users)
    
    S4H-linked accounts may omit password_hash. Standalone TLMS accounts use
    a versioned salted hash and can later be linked to S4H by normalized email.
    
    Extended with fields from system.md for gamification:
    - current_xp, discipline_score, level for tracking progress
    """
    __tablename__ = "users"
    
    # Primary Key - Internal ID for joining other tables
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # S4H User ID - CRITICAL: Bridge between two systems
    # This contains the ID received from S4H Auth
    s4h_user_id = Column(String(255), unique=True, index=True, nullable=False)

    # Basic Info (synced from S4H/LHU)
    email = Column(String(255), nullable=False)
    student_id = Column(String(50), unique=True, index=True, nullable=True)
    phone = Column(String(20), nullable=True)  # Phone number from LHU
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    password_hash = Column(String(512), nullable=True)
    
    # Role in TLMS system (stored as an array for backward compatibility).
    # Application policy allows exactly one role per account.
    roles = Column(
        ARRAY(String(50)),
        default=['candidate'],
        nullable=False
    )
    
    # Status
    status = Column(
        SQLEnum(UserStatus, values_callable=lambda x: [e.value for e in x]),
        default=UserStatus.ACTIVE,
        nullable=False
    )
    
    # Gamification Fields (from system.md)
    current_xp = Column(Integer, default=0, nullable=False)
    discipline_score = Column(Float, default=100.0, nullable=False)  # Default 100/100
    level = Column(Integer, default=1, nullable=False)
    reliability_score = Column(Float, default=100.0, nullable=False)
    member_score = Column(Float, default=0.0, nullable=False)
    promotion_progress = Column(Float, default=0.0, nullable=False)
    member_level = Column(
        SQLEnum(MemberLevel, values_callable=lambda x: [e.value for e in x]),
        default=MemberLevel.NEW,
        nullable=False
    )
    
    # Promotion tracking
    core_task_progress = Column(Float, default=0.0, nullable=False)  # Percentage 0-100
    is_ready_to_promote = Column(Boolean, default=False, nullable=False)

    # Attendance tracking (synced from S4H check-in system)
    last_attendance_date = Column(String(10), nullable=True)  # Format: "DD/MM/YYYY"
    morning_shift = Column(Boolean, default=False)  # Worked morning shift today
    afternoon_shift = Column(Boolean, default=False)  # Worked afternoon shift today
    evening_shift = Column(Boolean, default=False)  # Worked evening shift today
    is_late_today = Column(Boolean, default=False)  # Was late today

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User {self.email} (s4h_id={self.s4h_user_id})>"
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts)) or self.email
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return role in (self.roles or [])
    
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.has_role(UserRole.ADMIN.value)
    
    def is_mentor(self) -> bool:
        """Check if user is mentor"""
        return self.has_role(UserRole.MENTOR.value)

    def can_receive_ai_tasks(self) -> bool:
        """Official members should not receive automatic AI generated tasks."""
        return self.member_level != MemberLevel.OFFICIAL
    
    def add_role(self, role: str):
        """Set the account role while preserving the legacy array column."""
        self.roles = [role]
    
    def remove_role(self, role: str):
        """Remove a role from user"""
        if self.roles and role in self.roles:
            self.roles = [r for r in self.roles if r != role]
    
    @property
    def primary_role(self) -> str:
        """Get the highest priority role (for display)"""
        priority = [UserRole.ADMIN.value, UserRole.MENTOR.value, UserRole.MEMBER.value, UserRole.CANDIDATE.value]
        for role in priority:
            if role in (self.roles or []):
                return role
        return UserRole.CANDIDATE.value
    
    def calculate_level(self) -> int:
        """
        Calculate level based on XP
        Formula from system.md (simplified): Level increases every 100 XP
        Mentors and Admins effectively have max level for display purposes.
        """
        # Admin-only and mentor-only accounts have max level for management screens.
        # Multi-role test accounts that also learn as candidate/member still level by XP.
        has_learning_role = self.has_role(UserRole.CANDIDATE.value) or self.has_role(UserRole.MEMBER.value)
        if not has_learning_role and self.primary_role in [UserRole.MENTOR.value, UserRole.ADMIN.value]:
            return 99

        return max(1, (self.current_xp // 100) + 1)
    
    def check_promotion_eligibility(self, target_xp: int = 1000) -> bool:
        """
        Check if user meets "Golden Triangle" criteria for promotion
        From system.md:
        1. Core Task Progress = 100%
        2. Total XP >= Target XP (default 1000)
        3. Discipline Score >= 80/100
        """
        return (
            self.core_task_progress >= 100.0 and
            self.current_xp >= target_xp and
            self.discipline_score >= 80.0
        )
