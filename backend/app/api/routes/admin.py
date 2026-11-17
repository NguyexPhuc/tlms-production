"""
Admin Routes - System Administration
Includes sensitive operations with enhanced security
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.api.rbac import get_admin_user
from app.services.user_import import user_import_service
from app.services.lhu_student_sync import lhu_student_sync_service
from app.schemas.mongo_import import ImportResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Operations"])


@router.post("/import-users", response_model=ImportResult)
async def import_users_from_mongodb(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
    x_import_secret: str = Header(
        ...,
        description="Secret token for user import authorization",
        alias="X-Import-Secret"
    )
):
    """
    Import users from MongoDB to PostgreSQL
    
    Security Requirements:
    1. User must have Admin role
    2. Must provide valid X-Import-Secret header
    3. Connection string is read from environment variable only
    
    This endpoint:
    - Connects to MongoDB using configured connection string
    - Only imports users that DON'T exist in local DB (based on s4h_user_id)
    - Does NOT overwrite existing users
    - Imports in batches to avoid timeout
    
    Returns:
        ImportResult with statistics:
        - total_in_mongodb: Total users found in MongoDB
        - imported_count: Number of new users added
        - skipped_count: Number of users skipped (already exist)
        - error_count: Number of errors encountered
        - errors: List of error messages (max 10)
    """
    # Log import attempt (without sensitive info)
    admin_email = admin_user.email
    logger.info(f"User import initiated by admin: {admin_email}")

    # Call import service
    result = await user_import_service.import_users(
        db=db,
        secret_token=x_import_secret
    )

    # Log result
    if result.success:
        logger.info(
            f"Import completed by {admin_email}: "
            f"{result.imported_count} imported, "
            f"{result.skipped_count} skipped, "
            f"{result.error_count} errors"
        )
    else:
        logger.warning(f"Import failed by {admin_email}: {result.message}")
    
    return result


@router.get("/import-users/status")
async def get_import_status(
    admin_user: User = Depends(get_admin_user)
):
    """
    Get information about user import configuration
    
    Returns:
        Configuration status (without exposing sensitive data)
    """
    from app.core.config import get_settings
    settings = get_settings()
    
    # Don't expose actual connection string or token
    has_mongodb_config = bool(settings.MONGODB_CONNECTION_STRING)
    has_secret_token = bool(settings.USER_IMPORT_SECRET_TOKEN)
    
    return {
        "mongodb_configured": has_mongodb_config,
        "secret_token_configured": has_secret_token,
        "database": settings.MONGODB_DATABASE if has_mongodb_config else None,
        "collection": settings.MONGODB_USERS_COLLECTION if has_mongodb_config else None,
        "initiated_by": admin_user.email
    }


@router.post("/sync-student-ids", response_model=Dict[str, Any])
async def sync_student_ids_from_lhu(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
    user_ids: Optional[list] = Body(None, embed=True)
):
    """
    Sync Student IDs from LHU MySQL Database to TLMS PostgreSQL

    This endpoint:
    - Connects to LHU MySQL database (hmcdat_public)
    - Fetches all students from lhu_users table
    - Matches with TLMS users by email or phone
    - Updates student_id (uid) for matched users

    If user_ids is provided, only sync those specific users.
    Otherwise, sync all users.

    Security:
    - Requires Admin role

    Returns:
        SyncResult with statistics
    """
    # Get email before any await to avoid async issues
    admin_email = admin_user.email
    logger.info(f"Student ID sync initiated by admin: {admin_email}")
    
    try:
        result = await lhu_student_sync_service.sync_student_ids(
            db,
            user_ids=user_ids
        )
        
        if result.success:
            logger.info(f"Sync completed by {admin_email}: {result.message}")
        else:
            logger.warning(f"Sync failed by {admin_email}: {result.message}")
        
        return {
            "success": result.success,
            "message": result.message,
            "total_in_lhu": result.total_in_lhu,
            "matched_by_email": result.matched_by_email,
            "matched_by_phone": result.matched_by_phone,
            "updated_count": result.updated_count,
            "skipped_count": result.skipped_count,
            "error_count": result.error_count,
            "errors": result.errors
        }
        
    except Exception as e:
        logger.error(f"Sync failed with exception: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi đồng bộ: {str(e)}"
        )
