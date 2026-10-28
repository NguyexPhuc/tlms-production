"""
Role-based Access Control Dependencies
Check user roles for protected routes
Supports multiple roles per user
"""
from functools import wraps
from typing import List
from fastapi import Depends, HTTPException, status
from app.api.deps import get_current_user
from app.models.user import User, UserRole


class RoleChecker:
    """
    Dependency class to check if user has at least one of the required roles
    
    Usage:
        @router.get("/admin-only")
        async def admin_route(user: User = Depends(RoleChecker([UserRole.ADMIN]))):
            ...
    """
    
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = [r.value for r in allowed_roles]
    
    async def __call__(self, user: User = Depends(get_current_user)) -> User:
        # Check if user has at least one of the allowed roles
        user_roles = user.roles or []
        if not any(role in user_roles for role in self.allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bạn không có quyền truy cập. Yêu cầu một trong các role: {self.allowed_roles}"
            )
        return user


# Pre-defined role checkers for common use cases
require_admin = RoleChecker([UserRole.ADMIN])
require_mentor_or_admin = RoleChecker([UserRole.MENTOR, UserRole.ADMIN])
require_member_or_above = RoleChecker([UserRole.MEMBER, UserRole.MENTOR, UserRole.ADMIN])


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """Dependency that requires admin role"""
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Admin mới có quyền thực hiện thao tác này"
        )
    return user


async def get_mentor_or_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency that requires mentor or admin role"""
    if not (user.is_admin() or user.is_mentor()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Mentor hoặc Admin mới có quyền thực hiện thao tác này"
        )
    return user
