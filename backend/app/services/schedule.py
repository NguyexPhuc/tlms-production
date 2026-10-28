"""
Schedule Service - Business logic for schedule and attendance
"""
import logging
from typing import List, Optional, Tuple
from datetime import date, datetime, time, timedelta
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.models.schedule import Schedule, Attendance, Shift, AttendanceStatus, ClassSchedule, RegistrationType
from app.models.user import User
from app.schemas.schedule import ScheduleCreate
from app.services.lhu_api import lhu_api_service
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    ForbiddenException
)

logger = logging.getLogger(__name__)


# Shift time ranges (Vietnam timezone)
SHIFT_TIMES = {
    Shift.MORNING: (time(7, 30), time(11, 30)),   # 7:30 - 11:30
    Shift.AFTERNOON: (time(13, 0), time(17, 0)),   # 13:00 - 17:00
    Shift.EVENING: (time(18, 0), time(22, 0))     # 18:00 - 22:00
}

# Points configuration
DISCIPLINE_POINTS_PRESENT = 2  # +2 points for attendance
DISCIPLINE_PENALTY_ABSENT = -5  # -5 points for absence
DISCIPLINE_PENALTY_LATE = -2  # -2 points for late
BONUS_POINTS_EXTRA = 3  # +3 bonus for extra effort


class ScheduleService:
    """Service for schedule and attendance management"""
    
    # ============================================
    # Schedule Registration
    # ============================================
    
    async def create_schedule(
        self,
        db: AsyncSession,
        user: User,
        schedule_data: ScheduleCreate
    ) -> Schedule:
        """Create a single schedule registration"""
        # Validate date (must be future or today)
        if schedule_data.work_date < date.today():
            raise BadRequestException("Cannot register for past dates")
        
        # Check if already registered for this date + shift
        existing = await db.execute(
            select(Schedule).where(
                and_(
                    Schedule.user_id == user.id,
                    Schedule.work_date == schedule_data.work_date,
                    Schedule.shift == schedule_data.shift,
                    Schedule.is_cancelled == False
                )
            )
        )
        if existing.scalar_one_or_none():
            raise BadRequestException("Already registered for this date and shift")
        
        schedule = Schedule(
            user_id=user.id,
            work_date=schedule_data.work_date,
            shift=schedule_data.shift
        )
        
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        
        logger.info(f"Schedule created: {user.email} on {schedule_data.work_date} {schedule_data.shift.value}")
        return schedule
    
    async def create_week_schedules(
        self,
        db: AsyncSession,
        user: User,
        schedules_data: List[ScheduleCreate]
    ) -> List[Schedule]:
        """Create multiple schedules at once (weekly registration)"""
        created_schedules = []
        
        for schedule_data in schedules_data:
            try:
                schedule = await self.create_schedule(db, user, schedule_data)
                created_schedules.append(schedule)
            except BadRequestException as e:
                logger.warning(f"Skipped schedule creation: {e}")
                continue
        
        return created_schedules
    
    async def get_user_by_id(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Optional[User]:
        """Get user by ID"""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def cancel_schedule(
        self,
        db: AsyncSession,
        user: User,
        schedule_id: UUID,
        reason: Optional[str] = None
    ) -> Schedule:
        """Cancel a schedule registration"""
        result = await db.execute(
            select(Schedule).where(
                and_(
                    Schedule.id == schedule_id,
                    Schedule.user_id == user.id
                )
            )
        )
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            raise NotFoundException("Schedule not found")
        
        if schedule.is_cancelled:
            raise BadRequestException("Schedule already cancelled")
        
        if schedule.work_date < date.today():
            raise BadRequestException("Cannot cancel past schedules")
        
        schedule.is_cancelled = True
        schedule.cancelled_at = datetime.utcnow()
        schedule.cancel_reason = reason
        
        await db.commit()
        await db.refresh(schedule)
        
        logger.info(f"Schedule cancelled: {schedule_id}")
        return schedule
    
    async def get_user_schedules(
        self,
        db: AsyncSession,
        user: User,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_cancelled: bool = False
    ) -> List[Schedule]:
        """Get user's schedules"""
        query = select(Schedule).where(Schedule.user_id == user.id)
        
        if start_date:
            query = query.where(Schedule.work_date >= start_date)
        if end_date:
            query = query.where(Schedule.work_date <= end_date)
        if not include_cancelled:
            query = query.where(Schedule.is_cancelled == False)
        
        query = query.order_by(Schedule.work_date, Schedule.shift)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_week_schedules(
        self,
        db: AsyncSession,
        user: User,
        week_start: date
    ) -> List[Schedule]:
        """Get schedules for a specific week"""
        week_end = week_start + timedelta(days=6)
        
        # We also want to trigger sync if it hasn't been done?
        # User requirement: "automation every week".
        # If no work schedules exist, maybe try to sync? 
        # But for now, let's just return what exists.
        
        return await self.get_user_schedules(
            db, user, week_start, week_end, include_cancelled=True
        )

    async def get_user_class_schedules(
        self,
        db: AsyncSession,
        user: User,
        week_start: date
    ) -> List[ClassSchedule]:
        week_end = week_start + timedelta(days=6)
        stmt = select(ClassSchedule).where(
            ClassSchedule.user_id == user.id,
            ClassSchedule.start_datetime >= datetime.combine(week_start, time.min),
            ClassSchedule.end_datetime <= datetime.combine(week_end, time.max)
        )
        return list((await db.execute(stmt)).scalars().all())

    async def sync_student_schedule(
        self,
        db: AsyncSession,
        user: User,
        week_start: date,
        force_update: bool = False
    ) -> List[Schedule]:
        """
        Sync with LHU API and auto-generate working schedules
        
        Args:
            db: Database session
            user: Current user
            week_start: Start date of the week
            force_update: If True, force fetch from LHU even if data exists
            
        Returns:
            List of AUTO generated schedules
        """
        try:
            if not user.student_id:
                raise BadRequestException("Vui lòng cập nhật Mã sinh viên (Student ID) trước.")

            week_end = week_start + timedelta(days=6)
            
            # Check if we already have cache for this week
            if not force_update:
                stmt_check = select(ClassSchedule).where(
                    ClassSchedule.user_id == user.id,
                    ClassSchedule.start_datetime >= datetime.combine(week_start, time.min),
                    ClassSchedule.end_datetime <= datetime.combine(week_end, time.max)
                )
                existing = (await db.execute(stmt_check)).first()
                if existing:
                    # Cache hit: Return existing AUTO schedules
                    stmt_sched = select(Schedule).where(
                        Schedule.user_id == user.id,
                        Schedule.work_date >= week_start,
                        Schedule.work_date <= week_end,
                        Schedule.registration_type == RegistrationType.AUTO
                    )
                    return list((await db.execute(stmt_sched)).scalars().all())

            # 1. Fetch External Data
            raw_events = await lhu_api_service.fetch_student_schedule(user.student_id, week_start)
            parsed_events = lhu_api_service.parse_events(raw_events)

            # 2. Cleanup old class schedules for this week
            stmt = select(ClassSchedule).where(
                ClassSchedule.user_id == user.id,
                ClassSchedule.start_datetime >= datetime.combine(week_start, time.min),
                ClassSchedule.end_datetime <= datetime.combine(week_end, time.max)
            )
            existing_classes = (await db.execute(stmt)).scalars().all()
            for ec in existing_classes:
                await db.delete(ec)
                
            # 3. Insert new class schedules
            valid_class_schedules = []
            for evt in parsed_events:
                # Only track events inside the week range
                if week_start <= evt['start_datetime'].date() <= week_end:
                     cs = ClassSchedule(
                         user_id=user.id,
                         subject_name=evt['subject_name'],
                         room=evt['room'],
                         start_datetime=evt['start_datetime'],
                         end_datetime=evt['end_datetime'],
                         is_cancelled=evt['is_cancelled'],
                         description=evt['description']
                     )
                     db.add(cs)
                     if not evt['is_cancelled']:
                         valid_class_schedules.append(evt)
            
            # 4. Generate Work Schedules
            generated_schedules = []
            
            for i in range(7): # Mon to Sun
                current_date = week_start + timedelta(days=i)
                
                # Auto-registration logic: Skip Sunday (weekday == 6)
                if current_date.weekday() == 6:
                    continue

                for shift_type, (start_time, end_time) in SHIFT_TIMES.items():
                    shift_start = datetime.combine(current_date, start_time)
                    shift_end = datetime.combine(current_date, end_time)
                    
                    # Check Overlap
                    is_busy = False
                    for cs in valid_class_schedules:
                        if cs['start_datetime'] < shift_end and cs['end_datetime'] > shift_start:
                            is_busy = True
                            break
                    
                    # Check existing work schedule
                    # IMPORTANT: Use shift_type.value if shift is a string in DB, or just shift_type if enum
                    # Based on error, column is 'character varying' but we pass 'shift' enum.
                    # We should cast it.
                    stmt = select(Schedule).where(
                        Schedule.user_id == user.id,
                        Schedule.work_date == current_date,
                        Schedule.shift == shift_type.value
                    )
                    existing_schedule = (await db.execute(stmt)).scalar_one_or_none()
                    
                    if is_busy:
                        # If busy, ensure no AUTO schedule exists
                        if existing_schedule and existing_schedule.registration_type == RegistrationType.AUTO:
                             await db.delete(existing_schedule)
                    else:
                        # If free, auto register if not exists
                        if not existing_schedule:
                            new_sched = Schedule(
                                user_id=user.id,
                                work_date=current_date,
                                shift=shift_type.value,
                                registration_type=RegistrationType.AUTO,
                                is_cancelled=False
                            )
                            db.add(new_sched)
                            generated_schedules.append(new_sched)
                        elif existing_schedule.registration_type == RegistrationType.AUTO:
                             # Keep existing schedule state (even if cancelled)
                             generated_schedules.append(existing_schedule)

            await db.commit()
            return generated_schedules

        except BadRequestException:
            raise
        except Exception as e:
            logger.exception(f"Error syncing schedule for user {user.id}")
            # Don't rollback here - let the caller handle it
            raise BadRequestException(f"Lỗi đồng bộ lịch: {str(e)}")

    
    # ============================================
    # Attendance Tracking
    # ============================================
    
    async def check_in(
        self,
        db: AsyncSession,
        user: User,
        shift: Shift,
        notes: Optional[str] = None
    ) -> Attendance:
        """User checks in for work"""
        today = date.today()
        now = datetime.utcnow()
        
        # Check if already checked in today for this shift
        existing = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.user_id == user.id,
                    Attendance.work_date == today,
                    Attendance.shift == shift,
                    Attendance.check_in_time.isnot(None)
                )
            )
        )
        if existing.scalar_one_or_none():
            raise BadRequestException("Already checked in for this shift today")
        
        # Find matching schedule
        schedule_result = await db.execute(
            select(Schedule).where(
                and_(
                    Schedule.user_id == user.id,
                    Schedule.work_date == today,
                    Schedule.shift == shift,
                    Schedule.is_cancelled == False
                )
            )
        )
        schedule = schedule_result.scalar_one_or_none()
        
        # Create attendance record
        status_val = AttendanceStatus.PRESENT
        points = DISCIPLINE_POINTS_PRESENT
        bonus = 0
        
        # Calculate time (assuming UTC+7 for Vietnam)
        vn_now = now + timedelta(hours=7)
        check_in_time_local = vn_now.time()
        
        # Check Late
        if shift in SHIFT_TIMES:
            start_time, _ = SHIFT_TIMES[shift]
            # 15 mins grace period
            grace_time = (datetime.combine(today, start_time) + timedelta(minutes=15)).time()
            
            if check_in_time_local > grace_time:
                status_val = AttendanceStatus.LATE
                points = DISCIPLINE_PENALTY_LATE
        
        # Check Extra Effort (No Schedule)
        if not schedule:
             status_val = AttendanceStatus.EXTRA
             bonus = BONUS_POINTS_EXTRA
             points = 0 # Base points 0, only bonus? Or base points + bonus?
             # Reconcile logic (line 551) used: attendance.user.discipline_score += BONUS_POINTS_EXTRA
             # So points = BONUS_POINTS_EXTRA
             points = BONUS_POINTS_EXTRA
        
        attendance = Attendance(
            user_id=user.id,
            schedule_id=schedule.id if schedule else None,
            work_date=today,
            shift=shift,
            check_in_time=now,
            notes=notes,
            status=status_val,
            discipline_points_change=points,
            bonus_points=bonus,
            auto_reconciled=True,
            reconciled_at=now
        )
        
        # Update User Score immediately
        user.discipline_score += points
        
        db.add(attendance)
        db.add(user) # Ensure user is tracked
        await db.commit()
        await db.refresh(attendance)
        
        logger.info(f"Check-in: {user.email} - {status_val} ({points} pts)")
        return attendance
    
    async def check_out(
        self,
        db: AsyncSession,
        user: User,
        attendance_id: UUID,
        notes: Optional[str] = None
    ) -> Attendance:
        """User checks out from work"""
        result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.id == attendance_id,
                    Attendance.user_id == user.id
                )
            )
        )
        attendance = result.scalar_one_or_none()
        
        if not attendance:
            raise NotFoundException("Attendance record not found")
        
        if not attendance.check_in_time:
            raise BadRequestException("Must check in first")
        
        if attendance.check_out_time:
            raise BadRequestException("Already checked out")
        
        attendance.check_out_time = datetime.utcnow()
        if notes:
            attendance.notes = f"{attendance.notes or ''}\n{notes}".strip()
        
        await db.commit()
        await db.refresh(attendance)
        
        logger.info(f"Check-out: {user.email} at {attendance.check_out_time}")
        return attendance
    
    async def get_user_attendances(
        self,
        db: AsyncSession,
        user: User,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Attendance]:
        """Get user's attendance records"""
        query = select(Attendance).where(Attendance.user_id == user.id)
        
        if start_date:
            query = query.where(Attendance.work_date >= start_date)
        if end_date:
            query = query.where(Attendance.work_date <= end_date)
        
        query = query.order_by(Attendance.work_date.desc(), Attendance.check_in_time.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    # ============================================
    # Attendance Reconciliation
    # ============================================
    
    async def reconcile_attendance(
        self,
        db: AsyncSession,
        target_date: date
    ) -> int:
        """
        Reconcile attendance for a specific date
        Compare schedules vs actual attendance and assign points
        
        Returns: Number of records reconciled
        """
        # Get all schedules for this date (not cancelled)
        schedules_result = await db.execute(
            select(Schedule).options(selectinload(Schedule.user)).where(
                and_(
                    Schedule.work_date == target_date,
                    Schedule.is_cancelled == False
                )
            )
        )
        schedules = schedules_result.scalars().all()
        
        # Get all attendances for this date
        attendances_result = await db.execute(
            select(Attendance).options(selectinload(Attendance.user)).where(
                Attendance.work_date == target_date
            )
        )
        attendances = attendances_result.scalars().all()
        
        reconciled_count = 0
        
        # Process scheduled work
        for schedule in schedules:
            # Find matching attendance
            attendance = next(
                (a for a in attendances if a.user_id == schedule.user_id and a.shift == schedule.shift),
                None
            )
            
            if attendance:
                # Already reconciled? Skip to avoid double counting
                if attendance.auto_reconciled:
                    continue

                # Has schedule + Has attendance
                if attendance.check_in_time:
                    # Check if late
                    shift_start = SHIFT_TIMES[schedule.shift][0]
                    check_in_time = attendance.check_in_time.time()
                    
                    if check_in_time > shift_start:
                        # Late
                        attendance.status = AttendanceStatus.LATE
                        attendance.discipline_points_change = DISCIPLINE_PENALTY_LATE
                    else:
                        # On time - Present
                        attendance.status = AttendanceStatus.PRESENT
                        attendance.discipline_points_change = DISCIPLINE_POINTS_PRESENT
                    
                    # Update user discipline score
                    schedule.user.discipline_score += attendance.discipline_points_change
                    
                    attendance.auto_reconciled = True
                    attendance.reconciled_at = datetime.utcnow()
                    reconciled_count += 1
                    
                    logger.info(
                        f"Reconciled: {schedule.user.email} - {attendance.status.value} "
                        f"({attendance.discipline_points_change:+d} points)"
                    )
            else:
                # Has schedule + No attendance = Absent
                attendance = Attendance(
                    user_id=schedule.user_id,
                    schedule_id=schedule.id,
                    work_date=target_date,
                    shift=schedule.shift,
                    status=AttendanceStatus.ABSENT,
                    discipline_points_change=DISCIPLINE_PENALTY_ABSENT,
                    auto_reconciled=True,
                    reconciled_at=datetime.utcnow()
                )
                
                # Update user discipline score
                schedule.user.discipline_score += DISCIPLINE_PENALTY_ABSENT
                
                db.add(attendance)
                reconciled_count += 1
                
                logger.warning(
                    f"Absent: {schedule.user.email} on {target_date} {schedule.shift.value} "
                    f"({DISCIPLINE_PENALTY_ABSENT:+d} points)"
                )
        
        # Process extra effort (no schedule but has attendance)
        for attendance in attendances:
            if attendance.auto_reconciled:
                continue

            if not attendance.schedule_id and attendance.check_in_time:
                # Extra effort
                attendance.status = AttendanceStatus.EXTRA
                attendance.bonus_points = BONUS_POINTS_EXTRA
                attendance.user.discipline_score += BONUS_POINTS_EXTRA
                attendance.auto_reconciled = True
                attendance.reconciled_at = datetime.utcnow()
                reconciled_count += 1
                
                logger.info(
                    f"Extra effort: {attendance.user.email} on {target_date} "
                    f"(+{BONUS_POINTS_EXTRA} bonus points)"
                )
        
        await db.commit()
        
        logger.info(f"Reconciliation completed for {target_date}: {reconciled_count} records")
        return reconciled_count
    
    async def get_attendance_stats(
        self,
        db: AsyncSession,
        user: User,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """Get attendance statistics for a user"""
        # Build queries
        schedule_query = select(func.count(Schedule.id)).where(
            and_(
                Schedule.user_id == user.id,
                Schedule.is_cancelled == False
            )
        )
        
        attendance_query = select(
            func.count(Attendance.id),
            Attendance.status
        ).where(
            Attendance.user_id == user.id
        ).group_by(Attendance.status)
        
        points_query = select(
            func.sum(Attendance.discipline_points_change),
            func.sum(Attendance.bonus_points)
        ).where(
            Attendance.user_id == user.id
        )
        
        # Apply date filters
        if start_date:
            schedule_query = schedule_query.where(Schedule.work_date >= start_date)
            attendance_query = attendance_query.where(Attendance.work_date >= start_date)
            points_query = points_query.where(Attendance.work_date >= start_date)
        if end_date:
            schedule_query = schedule_query.where(Schedule.work_date <= end_date)
            attendance_query = attendance_query.where(Attendance.work_date <= end_date)
            points_query = points_query.where(Attendance.work_date <= end_date)
        
        # Execute queries
        total_scheduled = (await db.execute(schedule_query)).scalar() or 0
        
        attendance_counts = {}
        attendance_result = await db.execute(attendance_query)
        for count, status in attendance_result.all():
            attendance_counts[status.value] = count
        
        points_result = await db.execute(points_query)
        discipline_total, bonus_total = points_result.one()
        
        # Calculate stats
        total_attended = attendance_counts.get('present', 0) + attendance_counts.get('late', 0)
        attendance_rate = (total_attended / total_scheduled * 100) if total_scheduled > 0 else 0
        
        return {
            'total_scheduled': total_scheduled,
            'total_attended': total_attended,
            'total_absent': attendance_counts.get('absent', 0),
            'total_late': attendance_counts.get('late', 0),
            'total_extra': attendance_counts.get('extra', 0),
            'attendance_rate': round(attendance_rate, 1),
            'discipline_points_total': int(discipline_total or 0),
            'bonus_points_total': int(bonus_total or 0)
        }


schedule_service = ScheduleService()
