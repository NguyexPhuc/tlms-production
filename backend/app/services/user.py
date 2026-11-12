"""
User Service - Local user management with Lazy Sync strategy
Implements oauth.md section 4.3: User Sync Strategy
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserRole, UserStatus, MemberLevel
from app.schemas.auth import S4HUserInfo

logger = logging.getLogger(__name__)


class UserService:
    """
    Service for managing local user records
    
    Implements "Lazy Sync" strategy from oauth.md:
    - When authentication succeeds, check local database
    - If user doesn't exist: INSERT new record with s4h_user_id and email
    - If user exists: Update email if changed and continue
    """
    
    async def get_or_create_user(
        self,
        db: AsyncSession,
        s4h_user_info: S4HUserInfo
    ) -> User:
        """
        Get existing user or create new one based on S4H user info
        
        This implements the Lazy Sync strategy:
        - Query: Check if user with external_id (s4h_user_id) exists
        - If not: INSERT new record
        - If yes: Update email if changed
        
        Args:
            db: Database session
            s4h_user_info: User info from S4H /users/me endpoint
            
        Returns:
            Local User model instance
        """
        # Query by s4h_user_id (the bridge between systems)
        stmt = select(User).where(User.s4h_user_id == s4h_user_info.id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            email_match = (
                await db.execute(
                    select(User).where(func.lower(User.email) == str(s4h_user_info.email).lower())
                )
            ).scalar_one_or_none()
            if email_match is not None and email_match.s4h_user_id.startswith("local:"):
                email_match.s4h_user_id = s4h_user_info.id
                user = email_match
        
        if user is None:
            # User doesn't exist locally - create new record
            logger.info(f"Creating local user for S4H ID: {s4h_user_info.id}")

            user = User(
                s4h_user_id=s4h_user_info.id,
                email=s4h_user_info.email,
                phone=s4h_user_info.phone,  # Sync phone from S4H
                first_name=s4h_user_info.firstName,
                last_name=s4h_user_info.lastName,
                student_id=s4h_user_info.studentCode, # Sync student ID on creation
                roles=['candidate'],  # Default role for new users
                status=UserStatus.ACTIVE,
                current_xp=0,
                discipline_score=100.0,
                reliability_score=100.0,
                member_score=0.0,
                promotion_progress=0.0,
                member_level=MemberLevel.NEW,
                level=1,
                last_login_at=datetime.utcnow()
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)

            logger.info(f"Local user created: {user.id} for {user.email}")
        else:
            # User exists - update if needed
            updated = False

            # Update email if changed
            if user.email != s4h_user_info.email:
                logger.info(f"Updating email for user {user.id}: {user.email} -> {s4h_user_info.email}")
                user.email = s4h_user_info.email
                updated = True

            # Update phone if provided and changed
            if s4h_user_info.phone and user.phone != s4h_user_info.phone:
                logger.info(f"Updating phone for user {user.id}: {user.phone} -> {s4h_user_info.phone}")
                user.phone = s4h_user_info.phone
                updated = True

            # Update name if provided and changed
            if s4h_user_info.firstName and user.first_name != s4h_user_info.firstName:
                user.first_name = s4h_user_info.firstName
                updated = True

            if s4h_user_info.lastName and user.last_name != s4h_user_info.lastName:
                user.last_name = s4h_user_info.lastName
                updated = True

            # Update studentCode if provided and available in database
            if hasattr(s4h_user_info, 'studentCode') and s4h_user_info.studentCode and not user.student_id:
                user.student_id = s4h_user_info.studentCode
                updated = True

            # Update last login time
            user.last_login_at = datetime.utcnow()

            if updated:
                await db.flush()
                await db.refresh(user)

        return user
    
    async def get_user_by_id(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[User]:
        """Get user by internal ID"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_s4h_id(
        self,
        db: AsyncSession,
        s4h_user_id: str
    ) -> Optional[User]:
        """Get user by S4H external ID"""
        stmt = select(User).where(User.s4h_user_id == s4h_user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_user_login(
        self,
        db: AsyncSession,
        user: User
    ) -> User:
        """Update user's last login timestamp"""
        user.last_login_at = datetime.utcnow()
        await db.flush()
        await db.refresh(user)
        return user


# Singleton instance
user_service = UserService()
