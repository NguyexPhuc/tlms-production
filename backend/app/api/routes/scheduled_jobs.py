"""Authenticated callbacks for managed free-tier schedulers."""
from __future__ import annotations

import hmac
import logging
from enum import Enum
from typing import Awaitable, Callable

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import settings
from app.services.background_tasks import (
    open_weekly_cup_event,
    reset_daily_quests,
    run_zalo_daily_quiz_jobs,
    sync_all_user_schedules,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal/jobs", tags=["Internal Scheduled Jobs"])


class ScheduledJobName(str, Enum):
    DAILY_QUESTS = "daily-quests"
    WEEKLY_SCHEDULES = "weekly-schedules"
    WEEKLY_CUP = "weekly-cup"
    ZALO = "zalo"


def verify_scheduler_key(provided_key: str) -> None:
    if not settings.SCHEDULER_API_KEY:
        logger.error("SCHEDULER_API_KEY is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduled jobs are not configured",
        )
    if not hmac.compare_digest(provided_key, settings.SCHEDULER_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid scheduler key",
        )


@router.post("/{job_name}", include_in_schema=False)
async def run_scheduled_job(
    job_name: ScheduledJobName,
    x_scheduler_key: str = Header(..., alias="X-Scheduler-Key"),
):
    """Run one idempotent scheduler task using the existing TLMS services."""
    verify_scheduler_key(x_scheduler_key)
    handlers: dict[ScheduledJobName, Callable[[], Awaitable[object]]] = {
        ScheduledJobName.DAILY_QUESTS: reset_daily_quests,
        ScheduledJobName.WEEKLY_SCHEDULES: sync_all_user_schedules,
        ScheduledJobName.WEEKLY_CUP: open_weekly_cup_event,
        ScheduledJobName.ZALO: run_zalo_daily_quiz_jobs,
    }
    await handlers[job_name]()
    logger.info("Scheduled job %s completed", job_name.value)
    return {"success": True, "job": job_name.value}
