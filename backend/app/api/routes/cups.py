"""Weekly cup competition routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.cup import WeeklyCupDashboardResponse, WeeklyCupStartResponse, WeeklyCupSubmitRequest, WeeklyCupSubmitResponse
from app.services.cup import weekly_cup_service


router = APIRouter(prefix="/cups", tags=["Weekly Cups"])


@router.get("/weekly", response_model=WeeklyCupDashboardResponse)
async def get_weekly_cup_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current Friday cup event, quiz status, unique cups and quiz leaderboard."""
    return await weekly_cup_service.get_dashboard(db, current_user)


@router.post("/weekly/start", response_model=WeeklyCupStartResponse)
async def start_weekly_cup_quiz(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start the timed 20-question IT quiz for the current Friday cup event."""
    return await weekly_cup_service.start_current_quiz(db, current_user)


@router.post("/weekly/submit", response_model=WeeklyCupSubmitResponse)
async def submit_weekly_cup_quiz(
    request: WeeklyCupSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit quiz answers. Winner is decided by score, then fastest duration."""
    return await weekly_cup_service.submit_current_quiz(db, current_user, request.answers)
