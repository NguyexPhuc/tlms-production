"""
Profile Service - Business logic for user profile management
Handles:
- Profile statistics calculation
- Evidence management
- Auto-schedule based on class schedules
- Reward calculations
"""
import logging
from typing import List, Optional, Tuple, Dict
from datetime import date, datetime, timedelta
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.models.user import User
from app.models.task import Task, UserTask, TaskStatus, TaskType
from app.models.schedule import Schedule, Attendance, ClassSchedule, Shift, AttendanceStatus, RegistrationType
from app.models.profile import ProfileEvidence, EvidenceStatus
from app.schemas.profile import (
    ProfileEvidenceCreate,
    ProfileEvidenceUpdate,
    ProfileEvidenceVerify,
    ProfileEvidenceOut,
    ProfileStats,
    WorkScheduleStats,
    TaskStats,
    AchievementSummary,
    ProfileResponse,
    UserBasicInfo,
    AutoScheduleRequest,
    AutoScheduleResult,
    ScheduleConflict
)
from app.schemas.schedule import ScheduleCreate
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    ForbiddenException
)

logger = logging.getLogger(__name__)


class ProfileService:
    """Service for profile management"""
    
    # ============================================
    # Profile Evidence Management
    # ============================================
    
    async def create_evidence(
        self,
        db: AsyncSession,
        user: User,
        evidence_data: ProfileEvidenceCreate
    ) -> ProfileEvidence:
        """Create new profile evidence"""
        # Validate task if provided
        if evidence_data.task_id:
            task_result = await db.execute(
                select(Task).where(Task.id == evidence_data.task_id)
            )
            task = task_result.scalar_one_or_none()
            if not task:
                raise NotFoundException("Task not found")
        
        evidence = ProfileEvidence(
            user_id=user.id,
            task_id=evidence_data.task_id,
            title=evidence_data.title,
            description=evidence_data.description,
            evidence_links=evidence_data.evidence_links,
            tags=evidence_data.tags,
            is_public=evidence_data.is_public
        )
        
        db.add(evidence)
        await db.commit()
        await db.refresh(evidence)
        
        logger.info(f"Evidence created: {evidence.title} by user {user.email}")
        return evidence
    
    async def update_evidence(
        self,
        db: AsyncSession,
        user: User,
        evidence_id: UUID,
        evidence_data: ProfileEvidenceUpdate
    ) -> ProfileEvidence:
        """Update existing evidence"""
        result = await db.execute(
            select(ProfileEvidence).where(
                and_(
                    ProfileEvidence.id == evidence_id,
                    ProfileEvidence.user_id == user.id
                )
            )
        )
        evidence = result.scalar_one_or_none()
        
        if not evidence:
            raise NotFoundException("Evidence not found or access denied")
        
        # Update fields
        update_data = evidence_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(evidence, field, value)
        
        evidence.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(evidence)
        
        logger.info(f"Evidence updated: {evidence_id} by user {user.email}")
        return evidence
    
    async def verify_evidence(
        self,
        db: AsyncSession,
        verifier: User,
        evidence_id: UUID,
        verify_data: ProfileEvidenceVerify
    ) -> ProfileEvidence:
        """Verify evidence (Mentor/Admin only)"""
        if not (verifier.is_mentor() or verifier.is_admin()):
            raise ForbiddenException("Only mentors and admins can verify evidence")
        
        result = await db.execute(
            select(ProfileEvidence).where(ProfileEvidence.id == evidence_id)
        )
        evidence = result.scalar_one_or_none()
        
        if not evidence:
            raise NotFoundException("Evidence not found")
        
        evidence.status = verify_data.status
        evidence.verification_notes = verify_data.verification_notes
        evidence.is_featured = verify_data.is_featured
        evidence.verified_by_id = verifier.id
        evidence.verified_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(evidence)
        
        logger.info(f"Evidence {evidence_id} verified by {verifier.email}: {verify_data.status}")
        return evidence
    
    async def delete_evidence(
        self,
        db: AsyncSession,
        user: User,
        evidence_id: UUID
    ) -> None:
        """Delete evidence"""
        result = await db.execute(
            select(ProfileEvidence).where(
                and_(
                    ProfileEvidence.id == evidence_id,
                    ProfileEvidence.user_id == user.id
                )
            )
        )
        evidence = result.scalar_one_or_none()
        
        if not evidence:
            raise NotFoundException("Evidence not found or access denied")
        
        await db.delete(evidence)
        await db.commit()
        
        logger.info(f"Evidence deleted: {evidence_id} by user {user.email}")
    
    async def get_user_evidence(
        self,
        db: AsyncSession,
        user: User,
        include_pending: bool = True
    ) -> List[ProfileEvidence]:
        """Get all evidence for a user"""
        query = select(ProfileEvidence).where(ProfileEvidence.user_id == user.id)
        
        if not include_pending:
            query = query.where(ProfileEvidence.status == EvidenceStatus.VERIFIED)
        
        query = query.order_by(ProfileEvidence.created_at.desc())
        
        result = await db.execute(query)
        return result.scalars().all()
    
    # ============================================
    # Profile Statistics
    # ============================================
    
    async def calculate_work_schedule_stats(
        self,
        db: AsyncSession,
        user: User
    ) -> WorkScheduleStats:
        """Calculate work schedule and attendance statistics"""
        now = datetime.utcnow()
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Calculate hours per shift (4 hours each)
        HOURS_PER_SHIFT = 4.0
        
        # This week
        week_result = await db.execute(
            select(func.count(Schedule.id)).where(
                and_(
                    Schedule.user_id == user.id,
                    Schedule.work_date >= week_start,
                    Schedule.is_cancelled == False
                )
            )
        )
        week_shifts = week_result.scalar() or 0
        
        # This month
        month_result = await db.execute(
            select(func.count(Schedule.id)).where(
                and_(
                    Schedule.user_id == user.id,
                    Schedule.work_date >= month_start,
                    Schedule.is_cancelled == False
                )
            )
        )
        month_shifts = month_result.scalar() or 0
        
        # All time
        total_result = await db.execute(
            select(func.count(Schedule.id)).where(
                and_(
                    Schedule.user_id == user.id,
                    Schedule.is_cancelled == False
                )
            )
        )
        total_shifts = total_result.scalar() or 0
        
        # Attendance rate (based on attendances with PRESENT status)
        # Count present attendances
        present_result = await db.execute(
            select(func.count(Attendance.id)).where(
                and_(
                    Attendance.user_id == user.id,
                    Attendance.status == AttendanceStatus.PRESENT.value
                )
            )
        )
        present_count = present_result.scalar() or 0
        
        # Count total attendances
        total_result = await db.execute(
            select(func.count(Attendance.id)).where(Attendance.user_id == user.id)
        )
        total_attendance = total_result.scalar() or 0
        attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 100.0
        
        # Unique days worked
        days_result = await db.execute(
            select(func.count(func.distinct(Attendance.work_date))).where(
                and_(
                    Attendance.user_id == user.id,
                    Attendance.status == AttendanceStatus.PRESENT.value
                )
            )
        )
        total_days_worked = days_result.scalar() or 0
        
        return WorkScheduleStats(
            total_hours_this_week=week_shifts * HOURS_PER_SHIFT,
            total_hours_this_month=month_shifts * HOURS_PER_SHIFT,
            total_hours_all_time=total_shifts * HOURS_PER_SHIFT,
            attendance_rate=round(attendance_rate, 2),
            total_days_worked=total_days_worked
        )
    
    async def calculate_task_stats(
        self,
        db: AsyncSession,
        user: User
    ) -> TaskStats:
        """Calculate task completion statistics"""
        # Total completed tasks
        total_result = await db.execute(
            select(func.count(UserTask.id)).where(
                and_(
                    UserTask.user_id == user.id,
                    UserTask.status == TaskStatus.COMPLETED
                )
            )
        )
        total_completed = total_result.scalar() or 0
        logger.info(f"Task stats for {user.email}: total_completed={total_completed}")

        # Core tasks completed
        core_result = await db.execute(
            select(func.count(UserTask.id))
            .join(Task, UserTask.task_id == Task.id)
            .where(
                and_(
                    UserTask.user_id == user.id,
                    UserTask.status == TaskStatus.COMPLETED,
                    Task.type == TaskType.CORE
                )
            )
        )
        core_completed = core_result.scalar() or 0

        # Bounty tasks completed
        bounty_result = await db.execute(
            select(func.count(UserTask.id))
            .join(Task, UserTask.task_id == Task.id)
            .where(
                and_(
                    UserTask.user_id == user.id,
                    UserTask.status == TaskStatus.COMPLETED,
                    Task.type == TaskType.BOUNTY
                )
            )
        )
        bounty_completed = bounty_result.scalar() or 0

        # Total XP earned
        xp_result = await db.execute(
            select(func.sum(UserTask.xp_earned)).where(
                and_(
                    UserTask.user_id == user.id,
                    UserTask.status == TaskStatus.COMPLETED
                )
            )
        )
        total_xp = xp_result.scalar() or 0

        logger.info(f"Task stats: core={core_completed}, bounty={bounty_completed}, total_xp={total_xp}")

        return TaskStats(
            total_tasks_completed=total_completed,
            core_tasks_completed=core_completed,
            bounty_tasks_completed=bounty_completed,
            total_xp_earned=int(total_xp),
            current_level=user.calculate_level(),
            current_xp=user.current_xp,
            core_task_progress=user.core_task_progress
        )
    
    async def calculate_achievement_summary(
        self,
        db: AsyncSession,
        user: User
    ) -> AchievementSummary:
        """Calculate achievement summary"""
        # Total evidence
        total_result = await db.execute(
            select(func.count(ProfileEvidence.id)).where(
                ProfileEvidence.user_id == user.id
            )
        )
        total_evidence = total_result.scalar() or 0
        
        # Verified evidence
        verified_result = await db.execute(
            select(func.count(ProfileEvidence.id)).where(
                and_(
                    ProfileEvidence.user_id == user.id,
                    ProfileEvidence.status == EvidenceStatus.VERIFIED
                )
            )
        )
        verified_evidence = verified_result.scalar() or 0
        
        # Featured evidence
        featured_result = await db.execute(
            select(func.count(ProfileEvidence.id)).where(
                and_(
                    ProfileEvidence.user_id == user.id,
                    ProfileEvidence.is_featured == True
                )
            )
        )
        featured_evidence = featured_result.scalar() or 0
        
        # Collect all unique skill tags
        tags_result = await db.execute(
            select(ProfileEvidence.tags).where(
                and_(
                    ProfileEvidence.user_id == user.id,
                    ProfileEvidence.status == EvidenceStatus.VERIFIED
                )
            )
        )
        all_tags = set()
        for (tags,) in tags_result:
            if tags:
                all_tags.update(tags)
        
        return AchievementSummary(
            total_evidence=total_evidence,
            verified_evidence=verified_evidence,
            featured_evidence=featured_evidence,
            skill_tags=sorted(list(all_tags)),
            discipline_score=user.discipline_score,
            is_ready_to_promote=user.check_promotion_eligibility()
        )
    
    async def get_profile_stats(
        self,
        db: AsyncSession,
        user: User
    ) -> ProfileStats:
        """Get complete profile statistics"""
        work_schedule = await self.calculate_work_schedule_stats(db, user)
        tasks = await self.calculate_task_stats(db, user)
        achievements = await self.calculate_achievement_summary(db, user)
        
        return ProfileStats(
            work_schedule=work_schedule,
            tasks=tasks,
            achievements=achievements
        )
    
    # ============================================
    # Complete Profile
    # ============================================
    
    async def get_complete_profile(
        self,
        db: AsyncSession,
        user: User
    ) -> ProfileResponse:
        """Get complete user profile with all stats and evidence"""
        # Get stats
        stats = await self.get_profile_stats(db, user)
        
        # Get evidence
        evidence_list = await self.get_user_evidence(db, user, include_pending=True)
        evidence_out = [ProfileEvidenceOut.model_validate(e) for e in evidence_list]
        
        # Get recent tasks (last 10 completed)
        recent_tasks_result = await db.execute(
            select(UserTask)
            .options(selectinload(UserTask.task))
            .where(
                and_(
                    UserTask.user_id == user.id,
                    UserTask.status.in_([TaskStatus.COMPLETED, TaskStatus.SUBMITTED, TaskStatus.APPROVED])
                )
            )
            .order_by(UserTask.updated_at.desc())
            .limit(10)
        )
        recent_tasks = recent_tasks_result.scalars().all()
        recent_tasks_data = [
            {
                "task_id": str(ut.task_id),
                "title": ut.task.title if ut.task else "Unknown",
                "status": ut.status.value,
                "submitted_at": ut.submitted_at.isoformat() if ut.submitted_at else None,
                "xp_earned": ut.xp_earned
            }
            for ut in recent_tasks
        ]
        
        # Get upcoming schedules (next 7 days)
        today = date.today()
        next_week = today + timedelta(days=7)
        upcoming_result = await db.execute(
            select(Schedule)
            .where(
                and_(
                    Schedule.user_id == user.id,
                    Schedule.work_date >= today,
                    Schedule.work_date <= next_week,
                    Schedule.is_cancelled == False
                )
            )
            .order_by(Schedule.work_date, Schedule.shift)
        )
        upcoming_schedules = upcoming_result.scalars().all()
        upcoming_data = [
            {
                "date": s.work_date.isoformat(),
                "shift": s.shift,
                "registration_type": s.registration_type.value
            }
            for s in upcoming_schedules
        ]
        
        # Build user basic info
        user_info = UserBasicInfo(
            id=user.id,
            email=user.email,
            student_id=user.student_id,
            full_name=user.full_name,
            roles=user.roles or [],
            primary_role=user.primary_role
        )
        
        return ProfileResponse(
            user=user_info,
            stats=stats,
            evidence=evidence_out,
            recent_tasks=recent_tasks_data,
            upcoming_schedules=upcoming_data
        )
    
    # ============================================
    # Auto-Schedule based on Class Schedule
    # ============================================
    
    async def auto_register_work_schedule(
        self,
        db: AsyncSession,
        user: User,
        request: AutoScheduleRequest
    ) -> AutoScheduleResult:
        """
        Auto-register work schedules to fill 8 hours/day
        based on class schedule gaps
        """
        if not user.student_id:
            raise BadRequestException("User must have a student_id to use auto-schedule")
        
        conflicts = []
        schedules_created = 0
        week_end = request.week_start_date + timedelta(days=6)
        
        # Get class schedules for the week
        class_schedules_result = await db.execute(
            select(ClassSchedule).where(
                and_(
                    ClassSchedule.user_id == user.id,
                    ClassSchedule.class_date >= request.week_start_date,
                    ClassSchedule.class_date <= week_end
                )
            )
        )
        class_schedules = class_schedules_result.scalars().all()
        
        # Group by date
        class_by_date: Dict[date, List[ClassSchedule]] = {}
        for cs in class_schedules:
            if cs.class_date not in class_by_date:
                class_by_date[cs.class_date] = []
            class_by_date[cs.class_date].append(cs)
        
        # For each day in the week
        for day_offset in range(7):
            work_date = request.week_start_date + timedelta(days=day_offset)
            
            # Skip past dates
            if work_date < date.today():
                continue
            
            # Get class schedules for this day
            day_classes = class_by_date.get(work_date, [])
            
            # Determine which shifts are occupied by classes
            occupied_shifts = set()
            for cs in day_classes:
                # Check based on class times
                # Morning classes: 7:00-11:00 -> conflicts with MORNING shift
                # Afternoon classes: 13:00-17:00 -> conflicts with AFTERNOON shift
                # Evening classes: 18:00-22:00 -> conflicts with EVENING shift
                if cs.start_time and cs.end_time:
                    if cs.start_time < datetime.strptime("12:00", "%H:%M").time():
                        occupied_shifts.add(Shift.MORNING)
                    elif cs.start_time < datetime.strptime("17:00", "%H:%M").time():
                        occupied_shifts.add(Shift.AFTERNOON)
                    else:
                        occupied_shifts.add(Shift.EVENING)

            # Calculate needed shifts (up to 3 shifts = 12 hours)
            available_shifts = [s for s in [Shift.MORNING, Shift.AFTERNOON, Shift.EVENING] if s not in occupied_shifts]

            # Apply user preferences
            if request.prefer_morning and Shift.MORNING in available_shifts:
                preferred_shifts = [Shift.MORNING] + [s for s in available_shifts if s != Shift.MORNING]
            elif request.prefer_afternoon and Shift.AFTERNOON in available_shifts:
                preferred_shifts = [Shift.AFTERNOON] + [s for s in available_shifts if s != Shift.AFTERNOON]
            elif request.prefer_evening and Shift.EVENING in available_shifts:
                preferred_shifts = [Shift.EVENING] + [s for s in available_shifts if s != Shift.EVENING]
            else:
                preferred_shifts = available_shifts

            # Try to register up to 3 shifts to reach 12 hours (4 hours per shift)
            shifts_needed = min(3, len(preferred_shifts))
            
            for i in range(shifts_needed):
                if i >= len(preferred_shifts):
                    break
                
                shift = preferred_shifts[i]
                
                # Check if already registered
                existing = await db.execute(
                    select(Schedule).where(
                        and_(
                            Schedule.user_id == user.id,
                            Schedule.work_date == work_date,
                            Schedule.shift == shift.value,
                            Schedule.is_cancelled == False
                        )
                    )
                )
                
                if existing.scalar_one_or_none():
                    conflicts.append(ScheduleConflict(
                        date=work_date,
                        shift=shift.value,
                        reason="Already registered"
                    ))
                    continue
                
                # Create schedule with AUTO registration type
                schedule = Schedule(
                    user_id=user.id,
                    work_date=work_date,
                    shift=shift.value,
                    registration_type=RegistrationType.AUTO
                )
                db.add(schedule)
                schedules_created += 1
        
        # Commit all schedules
        await db.commit()
        
        success = schedules_created > 0
        message = f"Auto-registered {schedules_created} work schedules"
        if conflicts:
            message += f" ({len(conflicts)} conflicts skipped)"
        
        logger.info(f"Auto-schedule for {user.email}: {schedules_created} schedules created, {len(conflicts)} conflicts")
        
        return AutoScheduleResult(
            success=success,
            message=message,
            schedules_created=schedules_created,
            conflicts=conflicts
        )


# Singleton instance
profile_service = ProfileService()
