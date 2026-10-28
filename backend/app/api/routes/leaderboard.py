"""
Leaderboard Routes - Rankings and statistics
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.services.leaderboard import leaderboard_service
from app.schemas.leaderboard import (
    LeaderboardResponse,
    LeaderboardEntry,
    UserRankInfo
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get(
    "",
    response_model=LeaderboardResponse,
    summary="Bảng xếp hạng"
)
async def get_leaderboard(
    role: Optional[str] = Query(None, description="Filter by role: candidate, member, mentor, admin"),
    limit: int = Query(100, ge=1, le=500, description="Number of entries to return"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Lấy bảng xếp hạng theo XP
    
    - Xếp hạng theo: XP (cao nhất) → Level → Discipline Score
    - Có thể filter theo role
    - Trả về rank của user hiện tại (nếu đã đăng nhập)
    """
    entries, total_users, my_rank = await leaderboard_service.get_leaderboard(
        db,
        role_filter=role,
        limit=limit,
        current_user=current_user
    )
    
    return LeaderboardResponse(
        entries=[LeaderboardEntry(**entry) for entry in entries],
        total_users=total_users,
        my_rank=my_rank,
        updated_at=datetime.utcnow()
    )


@router.get(
    "/my-rank",
    response_model=UserRankInfo,
    summary="Thứ hạng của tôi"
)
async def get_my_rank(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy thông tin xếp hạng chi tiết của user hiện tại
    
    - Thứ hạng hiện tại
    - Percentile (top x%)
    - XP cần để vượt người phía trước
    """
    rank_info = await leaderboard_service.get_user_rank_info(db, current_user)
    
    return UserRankInfo(**rank_info)


@router.get(
    "/stats",
    summary="Thống kê leaderboard"
)
async def get_leaderboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy thống kê tổng quan về leaderboard
    
    - Tổng số user
    - XP trung bình
    - Level trung bình
    - Số người sẵn sàng thăng cấp
    """
    stats = await leaderboard_service.get_leaderboard_stats(db)
    return stats


@router.get(
    "/top/{limit}",
    summary="Top performers"
)
async def get_top_performers(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Lấy danh sách top performers
    
    - Top user có XP cao nhất
    """
    top_users = await leaderboard_service.get_top_performers(db, limit)
    
    return {
        'top_users': [
            {
                'rank': idx + 1,
                'email': user.email,
                'full_name': user.full_name,
                'level': user.level,
                'current_xp': user.current_xp,
                'primary_role': user.primary_role
            }
            for idx, user in enumerate(top_users)
        ]
    }
