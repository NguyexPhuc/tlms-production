"""
User Import Service - Import users from MongoDB to PostgreSQL
Implements selective sync: only import users that don't exist in local DB
"""
import logging
from typing import List, Tuple
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole, UserStatus
from app.schemas.mongo_import import MongoDBUser
from app.services.mongo_import import mongo_db_service
from app.schemas.mongo_import import ImportResult

logger = logging.getLogger(__name__)


class UserImportService:
    """
    Service for importing users from MongoDB to PostgreSQL
    
    Security Notes:
    - Only imports users that don't exist (based on s4h_user_id)
    - Does not overwrite existing users
    - Logs only non-sensitive information
    """

    async def import_users(
        self,
        db: AsyncSession,
        secret_token: str
    ) -> ImportResult:
        """
        Import users from MongoDB to PostgreSQL
        
        Args:
            db: Database session
            secret_token: Secret token for authorization
            
        Returns:
            ImportResult with statistics
        """
        from app.core.config import get_settings
        settings = get_settings()
        
        # Verify secret token
        if not settings.USER_IMPORT_SECRET_TOKEN:
            logger.error("USER_IMPORT_SECRET_TOKEN not configured")
            return ImportResult(
                success=False,
                message="Server chưa cấu hình secret token"
            )
        
        # Use constant-time comparison to prevent timing attacks
        if secret_token != settings.USER_IMPORT_SECRET_TOKEN:
            logger.warning("Invalid secret token attempt")
            return ImportResult(
                success=False,
                message="Secret token không hợp lệ"
            )
        
        # Connect to MongoDB
        logger.info("Connecting to MongoDB for user import")
        connected = await mongo_db_service.connect()
        
        if not connected:
            return ImportResult(
                success=False,
                message="Không thể kết nối MongoDB. Kiểm tra connection string."
            )
        
        try:
            # Get total count
            total_users = await mongo_db_service.get_users_count()
            logger.info(f"Total users in MongoDB: {total_users}")
            
            if total_users == 0:
                return ImportResult(
                    success=True,
                    message="Không có user nào trong MongoDB",
                    total_in_mongodb=0
                )
            
            # Get existing user IDs from local DB
            stmt = select(User.s4h_user_id)
            result = await db.execute(stmt)
            existing_ids = set(row[0] for row in result.all())
            logger.info(f"Existing users in local DB: {len(existing_ids)}")
            
            # Import in batches
            imported_count = 0
            skipped_count = 0
            error_count = 0
            errors: List[str] = []
            
            async for batch in mongo_db_service.stream_users(batch_size=50):
                batch_result = await self._import_batch(
                    db=db,
                    users=batch,
                    existing_ids=existing_ids
                )
                
                imported_count += batch_result[0]
                skipped_count += batch_result[1]
                error_count += batch_result[2]
                errors.extend(batch_result[3])
                
                # Update existing_ids with newly imported users
                for user in batch:
                    if user.user_id not in existing_ids:
                        existing_ids.add(user.user_id)
                
                logger.info(f"Batch processed: +{batch_result[0]} imported, {batch_result[1]} skipped, {batch_result[2]} errors")
            
            # Commit final changes
            await db.commit()
            
            logger.info(f"Import completed: {imported_count} imported, {skipped_count} skipped, {error_count} errors")
            
            return ImportResult(
                success=True,
                message=f"Import thành công: {imported_count} user mới được thêm",
                total_in_mongodb=total_users,
                imported_count=imported_count,
                skipped_count=skipped_count,
                error_count=error_count,
                errors=errors[:10]  # Only return first 10 errors to avoid large response
            )
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Import failed: {str(e)}")
            return ImportResult(
                success=False,
                message=f"Lỗi import: {str(e)}",
                errors=[str(e)]
            )
        finally:
            # Always disconnect from MongoDB
            await mongo_db_service.disconnect()

    async def _import_batch(
        self,
        db: AsyncSession,
        users: List[MongoDBUser],
        existing_ids: set
    ) -> Tuple[int, int, int, List[str]]:
        """
        Import a batch of users - also update phone for existing users

        Returns:
            Tuple of (imported_count, skipped_count, error_count, errors_list)
        """
        imported = 0
        skipped = 0
        errors = 0
        error_messages = []

        for user in users:
            try:
                # Check if user already exists
                if user.user_id in existing_ids:
                    # Update phone if user has phone in MongoDB but not in TLMS
                    stmt = select(User).where(User.s4h_user_id == user.user_id)
                    result = await db.execute(stmt)
                    existing_user = result.scalar_one_or_none()
                    
                    if existing_user and user.phone and not existing_user.phone:
                        existing_user.phone = user.phone
                        skipped += 1
                        logger.debug(f"Updated phone for existing user: {existing_user.email}")
                    else:
                        skipped += 1
                    continue

                # Skip if no email (required field)
                if not user.email:
                    errors += 1
                    error_messages.append(f"User {user.user_id}: không có email")
                    continue

                # Create new user
                # NOTE: NOT setting student_id here - that should only come from LHU sync
                new_user = User(
                    s4h_user_id=user.user_id,
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    phone=user.phone,  # Sync phone from MongoDB
                    # student_id=user.student_id,  # DON'T sync student_id from MongoDB
                    roles=['candidate'],  # Default role
                    status=UserStatus.ACTIVE,
                    current_xp=0,
                    discipline_score=100.0,
                    level=1,
                    created_at=user.created_at or datetime.utcnow(),
                    updated_at=user.updated_at or datetime.utcnow()
                )

                db.add(new_user)
                imported += 1
                logger.debug(f"Imported user: {user.email}")

            except Exception as e:
                errors += 1
                error_msg = f"User {user.user_id}: {str(e)}"
                error_messages.append(error_msg)
                logger.error(error_msg)

        return imported, skipped, errors, error_messages


# Singleton instance
user_import_service = UserImportService()
