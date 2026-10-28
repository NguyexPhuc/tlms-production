"""
Schedule API Routes
"""
import logging
from typing import List, Optional
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query, Path, Body
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.schedule import Shift
from app.services.schedule import schedule_service
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleResponse,
    ScheduleUpdate,
    AttendanceCheckIn,
    AttendanceCheckOut,
    AttendanceResponse,
    AttendanceStatsResponse,
    WeekScheduleRequest,
    WeekScheduleResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["schedules"])


# ============================================
# Schedule Registration
# ============================================

@router.post("/", response_model=ScheduleResponse)
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a single schedule registration"""
    schedule = await schedule_service.create_schedule(db, current_user, schedule_data)
    return schedule


@router.post("/week", response_model=List[ScheduleResponse])
async def create_week_schedules(
    week_data: WeekScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create multiple schedules for the week"""
    schedules = await schedule_service.create_week_schedules(
        db, current_user, week_data.schedules
    )
    return schedules


@router.get("/week/{week_start}", response_model=WeekScheduleResponse)
async def get_week_schedules(
    week_start: date = Path(..., description="Start of week (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get schedules for a specific week"""
    class_schedules = await schedule_service.get_user_class_schedules(db, current_user, week_start)
    schedules = await schedule_service.get_week_schedules(db, current_user, week_start)

    return WeekScheduleResponse(
        week_start=week_start,
        week_end=week_start + timedelta(days=6),
        schedules=schedules,
        class_schedules=class_schedules
    )


@router.post("/week/{week_start}/sync", response_model=List[ScheduleResponse])
async def sync_week_schedule(
    week_start: date = Path(..., description="Start of the week"),
    force: bool = Query(False, description="Force update from LHU API"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sync class schedule and auto-register work shifts"""
    return await schedule_service.sync_student_schedule(db, current_user, week_start, force_update=force)


# ============================================
# Admin / Reconciliation
# ============================================

from app.api.deps import require_admin

@router.post("/reconcile", dependencies=[Depends(require_admin)])
async def reconcile_daily_attendance(
    target_date: date = Body(..., embed=True, description="Date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    [Admin] Run daily reconciliation for ABESENCES.
    Note: Check-in updates Present/Late scores immediately.
    This runs to find people who missed their schedule entirely.
    """
    count = await schedule_service.reconcile_attendance(db, target_date)
    return {
        "message": f"Reconciliation completed for {target_date}",
        "processed_count": count
    }


@router.get("/my", response_model=List[ScheduleResponse])
async def get_my_schedules(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    include_cancelled: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's schedules"""
    schedules = await schedule_service.get_user_schedules(
        db, current_user, start_date, end_date, include_cancelled
    )
    return schedules


@router.patch("/{schedule_id}/cancel", response_model=ScheduleResponse)
async def cancel_schedule(
    schedule_id: UUID,
    reason: Optional[str] = Body(None, embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a schedule registration"""
    schedule = await schedule_service.cancel_schedule(db, current_user, schedule_id, reason)
    return schedule


# ============================================
# Attendance Tracking
# ============================================

@router.post("/check-in", response_model=AttendanceResponse)
async def check_in(
    check_in_data: AttendanceCheckIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check in for work"""
    attendance = await schedule_service.check_in(
        db, current_user, check_in_data.shift, check_in_data.notes
    )
    return attendance


@router.post("/check-out/{attendance_id}", response_model=AttendanceResponse)
async def check_out(
    attendance_id: UUID,
    check_out_data: AttendanceCheckOut,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check out from work"""
    attendance = await schedule_service.check_out(
        db, current_user, attendance_id, check_out_data.notes
    )
    return attendance


@router.get("/attendance/my", response_model=List[AttendanceResponse])
async def get_my_attendances(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's attendance records"""
    attendances = await schedule_service.get_user_attendances(
        db, current_user, start_date, end_date
    )
    return attendances


@router.get("/attendance/stats", response_model=AttendanceStatsResponse)
async def get_attendance_stats(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get attendance statistics"""
    stats = await schedule_service.get_attendance_stats(
        db, current_user, start_date, end_date
    )
    return AttendanceStatsResponse(**stats)


# ============================================
# Manager - View multiple users schedules
# ============================================

from app.api.deps import require_mentor

@router.get("/manager/users-schedules")
async def get_users_schedules_for_manager(
    week_start: date = Query(..., description="Start of week (YYYY-MM-DD)"),
    user_ids: str = Query(..., description="Comma-separated user IDs"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_mentor)
):
    """
    [Admin/Mentor] Get schedules and class schedules for multiple users
    Returns a dict with user_id as key and their schedule data as value
    """
    user_id_list = [uid.strip() for uid in user_ids.split(",") if uid.strip()]
    
    result = {}
    for user_id_str in user_id_list:
        try:
            user_id = UUID(user_id_str)
            user = await schedule_service.get_user_by_id(db, user_id)
            if user:
                schedules = await schedule_service.get_week_schedules(db, user, week_start)
                class_schedules = await schedule_service.get_user_class_schedules(db, user, week_start)
                result[str(user_id)] = {
                    "user": {
                        "id": str(user.id),
                        "full_name": user.full_name,
                        "email": user.email,
                        "student_id": user.student_id
                    },
                    "schedules": schedules,
                    "class_schedules": class_schedules
                }
        except Exception as e:
            logger.warning(f"Error getting schedule for user {user_id_str}: {e}")
            continue
    
    return result


# ============================================
# Admin - Background Scheduler Management
# ============================================

from app.services.background_tasks import (
    sync_all_user_schedules,
    force_sync_all_user_schedules,
    get_scheduler_status
)

@router.post("/admin/sync-all-users", dependencies=[Depends(require_admin)])
async def manually_sync_all_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    [Admin] Manually trigger schedule synchronization for all users with student IDs
    This forces a sync even if cached data exists
    """
    try:
        await sync_all_user_schedules()
        return {
            "success": True,
            "message": "Manual schedule sync for all users has been triggered",
            "detail": "Check server logs for sync results"
        }
    except Exception as e:
        logger.error(f"Manual sync failed: {str(e)}")
        return {
            "success": False,
            "message": "Failed to trigger manual sync",
            "error": str(e)
        }


@router.post("/admin/force-sync-all-users", dependencies=[Depends(require_admin)])
async def force_sync_all_users(
    week_start: Optional[date] = Body(None, embed=True, description="Optional week start (YYYY-MM-DD). Defaults to current week."),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    [Admin] Force sync schedules for ALL users that have student_id.
    Runs in background to avoid timeout. Returns immediately with job ID.
    Can optionally target a specific week.
    """
    import asyncio
    from datetime import timedelta
    
    try:
        effective_week_start = week_start
        if effective_week_start is None:
            today = date.today()
            effective_week_start = today - timedelta(days=today.weekday())
        
        logger.info(f"Force sync initiated by {current_user.email} for week {effective_week_start}")
        
        # Get count of users to sync
        result = await db.execute(
            select(func.count(User.id)).where(
                User.student_id.isnot(None),
                User.student_id != ""
            )
        )
        total_users = result.scalar() or 0
        
        # Start background task (don't await)
        asyncio.create_task(_force_sync_background(effective_week_start, current_user.email))
        
        return {
            "success": True,
            "message": f"Force sync started in background for {total_users} users",
            "week_start": str(effective_week_start),
            "total_users": total_users,
            "note": "Check server logs for completion status"
        }
    except Exception as e:
        logger.error(f"Force sync failed to start: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": "Failed to start force sync",
            "error": str(e)
        }


async def _force_sync_background(week_start: date, admin_email: str):
    """Background task to force sync all users"""
    try:
        summary = await force_sync_all_user_schedules(week_start=week_start)
        logger.info(f"=== FORCE SYNC COMPLETED by {admin_email} ===")
        logger.info(f"Week: {summary.get('week_start')}")
        logger.info(f"Total users: {summary.get('total_users')}")
        logger.info(f"Success: {summary.get('success_count')}")
        logger.info(f"Failed: {summary.get('error_count')}")
        if summary.get('failed_users'):
            logger.warning(f"Failed users: {summary.get('failed_users')[:10]}")  # Log first 10
    except Exception as e:
        logger.error(f"Background force sync failed: {str(e)}", exc_info=True)


@router.get("/admin/scheduler-status", dependencies=[Depends(require_admin)])
async def get_scheduler_info(
    current_user: User = Depends(require_admin)
):
    """
    [Admin] Get background scheduler status and job information
    Shows all scheduled jobs and their next run times
    """
    return get_scheduler_status()
