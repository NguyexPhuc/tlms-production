"""
Authentication Dependencies
Implements oauth.md section 4.2: Authentication Middleware

These dependencies extract and validate tokens, then perform user sync
"""
import logging
from fastapi import Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.core.exceptions import TokenExpiredException
from app.services.local_auth import local_auth_service
from app.services.s4h_auth import s4h_auth_service
from app.services.user import user_service
from app.models.user import User
from app.schemas.auth import S4HUserInfo

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


async def get_token_from_header(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Extract Bearer token from Authorization header
    
    Header format: Authorization: Bearer <access_token>
    """
    if credentials is None:
        return None
    return credentials.credentials


async def validate_token(token: str) -> S4HUserInfo:
    """
    Validate token with S4H Auth Service
    
    Token Introspection (oauth.md section 4.2):
    1. Call GET /users/me with token
    2. If 200 OK: Token valid, return user info
    3. If 401: Token expired/invalid, raise exception
    """
    return await s4h_auth_service.get_user_info(token)


async def get_current_user(
    token: Optional[str] = Depends(get_token_from_header),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Main authentication dependency
    
    Implements the complete auth flow from oauth.md:
    1. Extract token from header
    2. Validate token with S4H Auth (Token Introspection)
    3. Perform Lazy Sync - get or create local user
    4. Return local user for business logic
    
    Usage in routes:
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    if token is None:
        logger.warning("No authorization token provided")
        raise TokenExpiredException()
    
    if local_auth_service.is_local_token(token):
        user = await local_auth_service.get_user_from_token(db, token)
        logger.debug(f"Authenticated local dev user: {user.email} (ID: {user.id})")
        return user

    # Step 1: Validate token with S4H Auth
    s4h_user_info = await validate_token(token)
    
    # Step 2: Lazy Sync - get or create local user
    user = await user_service.get_or_create_user(db, s4h_user_info)
    
    logger.debug(f"Authenticated user: {user.email} (ID: {user.id})")
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(get_token_from_header),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication - returns None if no valid token
    
    Useful for endpoints that work differently for authenticated
    vs anonymous users
    """
    if token is None:
        return None
    
    try:
        if local_auth_service.is_local_token(token):
            return await local_auth_service.get_user_from_token(db, token)

        s4h_user_info = await validate_token(token)
        return await user_service.get_or_create_user(db, s4h_user_info)
    except TokenExpiredException:
        return None


# ============================================
# Role-based access dependencies
# ============================================

async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require admin role"""
    from app.core.exceptions import ForbiddenException
    if not current_user.is_admin():
        raise ForbiddenException("Admin access required")
    return current_user


async def require_mentor(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require mentor or admin role"""
    from app.core.exceptions import ForbiddenException
    if not (current_user.is_mentor() or current_user.is_admin()):
        raise ForbiddenException("Mentor access required")
    return current_user


async def require_member(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require member or higher role"""
    from app.core.exceptions import ForbiddenException
    if not current_user.has_role('member') and not current_user.is_mentor() and not current_user.is_admin():
        raise ForbiddenException("Member access required")
    return current_user
