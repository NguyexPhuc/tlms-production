"""
Leaderboard Schemas - Request/Response models
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID


class LeaderboardEntry(BaseModel):
    """Single entry in leaderboard"""
    rank: int
    user_id: UUID
    email: str
    full_name: Optional[str]
    roles: List[str]
    primary_role: str
    level: int
    current_xp: int
    discipline_score: float
    core_task_progress: float
    completed_tasks: int
    is_ready_to_promote: bool
    
    class Config:
        from_attributes = True


class LeaderboardResponse(BaseModel):
    """Leaderboard rankings"""
    entries: List[LeaderboardEntry]
    total_users: int
    my_rank: Optional[int] = None
    updated_at: datetime


class UserRankInfo(BaseModel):
    """User's personal ranking info"""
    rank: int
    total_users: int
    percentile: float
    current_xp: int
    next_rank_xp: Optional[int] = None
    xp_to_next_rank: Optional[int] = None
