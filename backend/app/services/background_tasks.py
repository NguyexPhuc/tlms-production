"""
Background Tasks Service - Automatic schedule synchronization
"""
import asyncio
import logging
import pytz
from datetime import date, datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.student_id import is_valid_student_id
from app.models.user import User, UserRole, UserStatus
from app.services.cup import weekly_cup_service
from app.services.quest import daily_quest_service
from app.services.schedule import schedule_service
from app.services.zalo_quiz import zalo_quiz_service

logger = logging.getLogger(__name__)

settings = get_settings()

# Vietnam timezone (UTC+7)
VN_TIMEZONE = pytz.timezone('Asia/Ho_Chi_Minh')

# Global scheduler instance with Vietnam timezone
scheduler = AsyncIOScheduler(timezone=VN_TIMEZONE)


def _is_syncable_student_id(student_id: Optional[str]) -> bool:
    """Only nine-digit LHU student identifiers can be synchronized."""
    return is_valid_student_id(student_id)


async def _run_with_retry(
    job_name: str,
    operation: Callable[[], Awaitable[Any]],
    attempts: int = 3,
) -> Any:
    """Retry transient integration/database failures and preserve a failed job signal."""
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except Exception:
            if attempt >= attempts:
                logger.exception("Background job %s failed after %s attempts", job_name, attempts)
                raise
            delay = 2 ** (attempt - 1)
            logger.warning(
                "Background job %s failed on attempt %s/%s; retrying in %ss",
                job_name,
                attempt,
                attempts,
                delay,
                exc_info=True,
            )
            await asyncio.sleep(delay)


async def _sync_all_user_schedules_for_week(
    week_start: date,
    force_update: bool = True,
    source: str = "system"
) -> Dict[str, Any]:
    """Sync schedules for active learners having a real student ID."""
    logger.info(
        "Starting %s schedule sync for week %s...",
        source,
        week_start.isoformat()
    )

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False
    )

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )

    try:
        # Get list of users to sync (using a separate session)
        async with async_session() as list_session:
            result = await list_session.execute(
                select(User).where(
                    User.student_id.isnot(None),
                    User.student_id != "",
                    User.status == UserStatus.ACTIVE,
                    or_(
                        User.roles.any(UserRole.CANDIDATE.value),
                        User.roles.any(UserRole.MEMBER.value),
                    ),
                )
            )
            users_to_sync = [
                user for user in result.scalars().all()
                if _is_syncable_student_id(user.student_id)
            ]

        total_users = len(users_to_sync)
        logger.info("Found %s users with student IDs to sync", total_users)

        if total_users == 0:
            return {
                "week_start": week_start.isoformat(),
                "total_users": 0,
                "success_count": 0,
                "error_count": 0,
                "failed_users": []
            }

        success_count = 0
        error_count = 0
        failed_users = []

        # Process each user in a separate session to avoid rollback issues
        for user in users_to_sync:
            # Create a new session for each user
            async with async_session() as db:
                try:
                    await schedule_service.sync_student_schedule(
                        db=db,
                        user=user,
                        week_start=week_start,
                        force_update=force_update
                    )
                    await db.commit()
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    failed_users.append(
                        {
                            "user_id": str(user.id),
                            "email": user.email,
                            "student_id": user.student_id,
                            "error": str(e)
                        }
                    )
                    logger.error(
                        "Failed to sync schedule for %s (%s): %s",
                        user.email,
                        user.student_id,
                        str(e)
                    )
                    # Don't call rollback here - async with will handle it

        summary = {
            "week_start": week_start.isoformat(),
            "total_users": total_users,
            "success_count": success_count,
            "error_count": error_count,
            "failed_users": failed_users
        }

        logger.info(
            "Schedule sync completed for week %s: %s succeeded, %s failed",
            week_start.isoformat(),
            success_count,
            error_count
        )
        return summary
        
    finally:
        await engine.dispose()


async def sync_all_user_schedules():
    """
    Background job: Sync schedules for all users with student IDs
    Runs weekly on Monday at 00:00 (or configurable)
    """
    async def operation():
        # Get the start of current week (Monday)
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        return await _sync_all_user_schedules_for_week(
            week_start=week_start,
            force_update=True,
            source="automatic"
        )

    await _run_with_retry("weekly_schedule_sync", operation)


async def reset_daily_quests():
    """
    Background job: expire old Daily Quests and generate a new set.
    Runs daily at the configured Vietnam-time reset hour.
    """
    async def operation():
        async with AsyncSessionLocal() as db:
            return await daily_quest_service.reset_daily_quests_for_all(db)

    await _run_with_retry("daily_quest_reset", operation)


async def open_weekly_cup_event():
    """
    Background job: finalize expired cup events and open the current Friday cup event.
    Runs weekly at the configured Vietnam-time weekday/hour.
    """
    async def operation():
        async with AsyncSessionLocal() as db:
            result = await weekly_cup_service.ensure_current_event(db)
            await db.commit()
            return result

    await _run_with_retry("weekly_cup_event", operation)


async def run_zalo_daily_quiz_jobs():
    """Poll runtime Zalo settings, expire sessions, retry failures, and send due messages."""
    async def operation():
        async with AsyncSessionLocal() as db:
            return await zalo_quiz_service.run_scheduled_jobs(db)

    await _run_with_retry("zalo_daily_quiz_jobs", operation)


async def force_sync_all_user_schedules(week_start: Optional[date] = None) -> Dict[str, Any]:
    """Manual admin operation to force sync all schedules for users with student_id."""
    effective_week_start = week_start
    if effective_week_start is None:
        today = date.today()
        effective_week_start = today - timedelta(days=today.weekday())

    return await _sync_all_user_schedules_for_week(
        week_start=effective_week_start,
        force_update=True,
        source="manual-admin"
    )


async def sync_next_week_schedules():
    """
    Background job: Sync schedules for next week
    Runs on Friday at 18:00 to prepare next week's schedules
    [DISABLED - Use weekly sync on Monday only]
    """
    pass


def start_scheduler():
    """
    Start the background scheduler
    Called during application startup
    """
    if scheduler.running:
        logger.warning("Scheduler is already running")
        return
    
    try:
        daily_quest_reset_hour = max(0, min(settings.DAILY_QUEST_RESET_HOUR, 23))
        weekly_cup_open_weekday = max(0, min(settings.WEEKLY_CUP_OPEN_WEEKDAY, 6))
        weekly_cup_open_hour = max(0, min(settings.WEEKLY_CUP_OPEN_HOUR, 23))

        # Weekly sync: Every Monday at 00:00 (midnight)
        scheduler.add_job(
            sync_all_user_schedules,
            trigger=CronTrigger(day_of_week=0, hour=0, minute=0),  # Monday 00:00
            id="weekly_schedule_sync",
            name="Weekly schedule sync for all users",
            replace_existing=True,
            max_instances=1
        )

        scheduler.add_job(
            reset_daily_quests,
            trigger=CronTrigger(hour=daily_quest_reset_hour, minute=0),
            id="daily_quest_reset",
            name="Daily Quest reset and generation",
            replace_existing=True,
            max_instances=1
        )

        scheduler.add_job(
            reset_daily_quests,
            trigger=DateTrigger(run_date=datetime.now(VN_TIMEZONE) + timedelta(seconds=5)),
            id="daily_quest_startup_bootstrap",
            name="Daily Quest startup bootstrap",
            replace_existing=True,
            max_instances=1
        )

        scheduler.add_job(
            open_weekly_cup_event,
            trigger=CronTrigger(day_of_week=weekly_cup_open_weekday, hour=weekly_cup_open_hour, minute=0),
            id="weekly_cup_event",
            name="Weekly Cup event open/finalize",
            replace_existing=True,
            max_instances=1
        )

        scheduler.add_job(
            run_zalo_daily_quiz_jobs,
            trigger=CronTrigger(minute="*"),
            id="zalo_daily_quiz_jobs",
            name="Zalo Daily Quiz dispatch, reminder, expiry and retry",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

        scheduler.add_job(
            open_weekly_cup_event,
            trigger=DateTrigger(run_date=datetime.now(VN_TIMEZONE) + timedelta(seconds=10)),
            id="weekly_cup_startup_bootstrap",
            name="Weekly Cup startup bootstrap",
            replace_existing=True,
            max_instances=1
        )
        
        scheduler.start()
        logger.info("✓ Background scheduler started successfully")
        logger.info("  - Weekly sync: Every Monday at 00:00 (Vietnam Time - UTC+7)")
        logger.info("  - Daily Quest reset: Every day at %02d:00 (Vietnam Time - UTC+7)", daily_quest_reset_hour)
        logger.info(
            "  - Weekly Cup event: weekday %s at %02d:00 (Vietnam Time - UTC+7)",
            weekly_cup_open_weekday,
            weekly_cup_open_hour,
        )
        logger.info("  - Daily Quest bootstrap: Once after backend startup")
        logger.info("  - Weekly Cup bootstrap: Once after backend startup")
        logger.info("  - Zalo Daily Quiz: Check runtime schedule every minute")
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}", exc_info=True)
        raise


def stop_scheduler():
    """
    Stop the background scheduler
    Called during application shutdown
    """
    if not scheduler.running:
        logger.warning("Scheduler is not running")
        return
    
    try:
        scheduler.shutdown(wait=False)
        logger.info("✓ Background scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {str(e)}")


def get_scheduler_status():
    """
    Get scheduler status and job information
    """
    return {
        "running": scheduler.running,
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "trigger": str(job.trigger),
                "next_run_time": str(job.next_run_time) if job.next_run_time else None
            }
            for job in scheduler.get_jobs()
        ]
    }
