"""
Leaderboard Service - Rankings and statistics
"""
import logging
from typing import List, Optional, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.user import User, UserStatus, UserRole
from app.models.task import UserTask, TaskStatus

logger = logging.getLogger(__name__)


class LeaderboardService:
    """Service for leaderboard and rankings"""
    
    async def get_leaderboard(
        self,
        db: AsyncSession,
        role_filter: Optional[str] = None,
        limit: int = 100,
        current_user: Optional[User] = None
    ) -> Tuple[List[dict], int, Optional[int]]:
        """
        Get leaderboard rankings
        
        Returns:
            - List of user entries with rank
            - Total number of users
            - Current user's rank (if provided)
        """
        # Base query - only active users
        # Exclude mentors and admins
        query = select(User).where(
             User.status == UserStatus.ACTIVE,
             ~User.roles.contains([UserRole.ADMIN.value]),
             ~User.roles.contains([UserRole.MENTOR.value])
        )
        
        # Filter by role if specified
        if role_filter:
            query = query.where(User.roles.contains([role_filter]))
        
        # Order by XP (descending), then by level, then by discipline score
        query = query.order_by(
            User.current_xp.desc(),
            User.level.desc(),
            User.discipline_score.desc()
        )
        
        # Get all users for ranking
        result = await db.execute(query)
        all_users = result.scalars().all()
        
        # Get completed tasks count for each user
        completed_tasks_query = select(
            UserTask.user_id,
            func.count(UserTask.id).label('completed_count')
        ).where(
            UserTask.status == TaskStatus.COMPLETED
        ).group_by(UserTask.user_id)
        
        completed_result = await db.execute(completed_tasks_query)
        completed_tasks_map = {
            str(user_id): count 
            for user_id, count in completed_result.all()
        }
        
        # Build leaderboard entries with ranks
        entries = []
        current_user_rank = None
        
        for rank, user in enumerate(all_users[:limit], start=1):
            entry = {
                'rank': rank,
                'user_id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'roles': user.roles or [],
                'primary_role': user.primary_role,
                'level': user.level,
                'current_xp': user.current_xp,
                'discipline_score': user.discipline_score,
                'core_task_progress': user.core_task_progress,
                'completed_tasks': completed_tasks_map.get(str(user.id), 0),
                'is_ready_to_promote': user.is_ready_to_promote
            }
            entries.append(entry)
            
            # Track current user's rank
            if current_user and user.id == current_user.id:
                current_user_rank = rank
        
        # If current user not in top limit, find their rank
        if current_user and current_user_rank is None:
            for rank, user in enumerate(all_users, start=1):
                if user.id == current_user.id:
                    current_user_rank = rank
                    break
        
        return entries, len(all_users), current_user_rank
    
    async def get_user_rank_info(
        self,
        db: AsyncSession,
        user: User
    ) -> dict:
        """Get detailed ranking info for a specific user"""
        # Order by XP (descending), then by level, then by discipline score
        
        # NOTE: primary_role is a python @property, NOT a database column.
        # We cannot filter by it in SQL.
        # We must filter by the 'roles' column (ARRAY).
        # Exclude users who have ADMIN or MENTOR roles in their roles array.
        
        # Base query: Active users only
        query = select(User).where(User.status == UserStatus.ACTIVE)
        
        # Exclude mentors and admins by checking if the roles array strictly DOES NOT contain these roles.
        # PostgreSQL Array operator for "NOT contains" is a bit tricky in SQLAlchemy.
        # Easier logic: Filter where NOT (roles @> ['admin']) AND NOT (roles @> ['mentor'])
        query = query.where(
            ~User.roles.contains([UserRole.ADMIN.value]),
            ~User.roles.contains([UserRole.MENTOR.value])
        )
        
        query = query.order_by(
            User.current_xp.desc(),
            User.level.desc(),
            User.discipline_score.desc()
        )
        
        result = await db.execute(query)
        all_users = result.scalars().all()
        
        # Find user's rank
        rank = None
        for idx, u in enumerate(all_users, start=1):
            if u.id == user.id:
                rank = idx
                break
        
        total_users = len(all_users)
        percentile = ((total_users - rank) / total_users * 100) if rank else 0
        
        # Find next ranked user (user above)
        next_rank_xp = None
        xp_to_next = None
        if rank and rank > 1:
            next_user = all_users[rank - 2]  # rank-1 in 0-indexed list
            next_rank_xp = next_user.current_xp
            xp_to_next = max(0, next_rank_xp - user.current_xp + 1)
        
        return {
            'rank': rank or total_users,
            'total_users': total_users,
            'percentile': round(percentile, 1),
            'current_xp': user.current_xp,
            'next_rank_xp': next_rank_xp,
            'xp_to_next_rank': xp_to_next
        }
    
    async def get_top_performers(
        self,
        db: AsyncSession,
        limit: int = 10,
        time_period: str = 'all'  # 'all', 'month', 'week'
    ) -> List[User]:
        """Get top performing users"""
        # For now, just return top by XP
        # In future, can add time-based filtering
        query = select(User).where(
            User.status == UserStatus.ACTIVE,
            ~User.roles.contains([UserRole.ADMIN.value]),
            ~User.roles.contains([UserRole.MENTOR.value])
        ).order_by(
            User.current_xp.desc()
        ).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_leaderboard_stats(
        self,
        db: AsyncSession
    ) -> dict:
        """Get overall leaderboard statistics"""
        # Total active users
        total_query = select(func.count(User.id)).where(
            User.status == UserStatus.ACTIVE
        )
        total_result = await db.execute(total_query)
        total_users = total_result.scalar() or 0
        
        # Average XP
        avg_xp_query = select(func.avg(User.current_xp)).where(
            User.status == UserStatus.ACTIVE
        )
        avg_xp_result = await db.execute(avg_xp_query)
        avg_xp = avg_xp_result.scalar() or 0
        
        # Average level
        avg_level_query = select(func.avg(User.level)).where(
            User.status == UserStatus.ACTIVE
        )
        avg_level_result = await db.execute(avg_level_query)
        avg_level = avg_level_result.scalar() or 1
        
        # Highest XP
        max_xp_query = select(func.max(User.current_xp)).where(
            User.status == UserStatus.ACTIVE
        )
        max_xp_result = await db.execute(max_xp_query)
        max_xp = max_xp_result.scalar() or 0
        
        # Users ready for promotion
        ready_query = select(func.count(User.id)).where(
            and_(
                User.status == UserStatus.ACTIVE,
                User.is_ready_to_promote == True
            )
        )
        ready_result = await db.execute(ready_query)
        ready_count = ready_result.scalar() or 0
        
        return {
            'total_active_users': total_users,
            'average_xp': round(avg_xp, 0),
            'average_level': round(avg_level, 1),
            'highest_xp': max_xp,
            'ready_for_promotion': ready_count
        }


leaderboard_service = LeaderboardService()
