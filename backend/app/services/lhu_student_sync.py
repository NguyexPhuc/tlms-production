"""
LHU Student Sync Service
Sync student IDs from LHU MySQL database to TLMS PostgreSQL
Match by email or phone number
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import aiomysql
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LHUStudent:
    """LHU Student data from MySQL"""
    id: int
    uid: str  # This is the student ID (mã sinh viên)
    username: str
    fullname: str
    gender: Optional[str]
    groupname: Optional[str]
    dob: Optional[str]
    hometown: Optional[str]
    address: Optional[str]
    ethnic: Optional[str]
    nation: Optional[str]
    citizen_id: Optional[str]
    status: Optional[int]
    email: Optional[str]
    phone: Optional[str]
    count: Optional[int]


@dataclass
class SyncResult:
    """Result of sync operation"""
    success: bool
    message: str
    total_in_lhu: int = 0
    matched_by_email: int = 0
    matched_by_phone: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class LHUStudentSyncService:
    """
    Service for syncing student IDs from LHU MySQL to TLMS PostgreSQL
    
    Matching strategy:
    1. Match by email (primary)
    2. Match by phone (fallback)
    """

    def __init__(self):
        self.lhu_db_config = {
            'host': settings.LHU_MYSQL_HOST,
            'port': settings.LHU_MYSQL_PORT,
            'user': settings.LHU_MYSQL_USER,
            'password': settings.LHU_MYSQL_PASSWORD,
            'db': settings.LHU_MYSQL_DATABASE,
            'autocommit': True
        }

    async def get_lhu_students(self) -> List[LHUStudent]:
        """
        Fetch all students from LHU MySQL database
        
        Returns:
            List of LHUStudent objects
        """
        students = []
        conn = None
        
        try:
            logger.info("Connecting to LHU MySQL database...")
            conn = await aiomysql.connect(**self.lhu_db_config)
            cursor = await conn.cursor()
            
            # Query all students from lhu_users table
            query = """
                SELECT id, uid, username, fullname, gender, groupname, 
                       dob, hometown, address, ethnic, nation, citizen_id, 
                       status, email, phone, count
                FROM lhu_users
                WHERE status IS NOT NULL
            """
            
            await cursor.execute(query)
            rows = await cursor.fetchall()
            
            for row in rows:
                try:
                    student = LHUStudent(
                        id=row[0],
                        uid=str(row[1]) if row[1] else None,
                        username=row[2] or '',
                        fullname=row[3] or '',
                        gender=row[4],
                        groupname=row[5],
                        dob=str(row[6]) if row[6] else None,
                        hometown=row[7],
                        address=row[8],
                        ethnic=row[9],
                        nation=row[10],
                        citizen_id=row[11],
                        status=row[12],
                        email=row[13],
                        phone=row[14],
                        count=row[15]
                    )
                    students.append(student)
                except Exception as e:
                    logger.warning(f"Error parsing student row: {str(e)}")
                    continue
            
            logger.info(f"Found {len(students)} students in LHU MySQL")

            cursor.close()

        except Exception as e:
            logger.error(f"Failed to fetch LHU students: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
        
        return students

    async def sync_student_ids(
        self,
        db_session,
        user_ids: Optional[List[str]] = None
    ) -> SyncResult:
        """
        Sync student IDs from LHU MySQL to TLMS PostgreSQL
        
        Args:
            db_session: SQLAlchemy async session
            user_ids: Optional list of TLMS user IDs to sync. 
                     If None, sync all users.
            
        Returns:
            SyncResult with statistics
        """
        from sqlalchemy import select
        from app.models.user import User
        
        result = SyncResult(success=False, message="")

        try:
            # Step 1: Fetch all students from LHU MySQL
            logger.info("Step 1: Fetching students from LHU MySQL...")
            lhu_students = await self.get_lhu_students()
            result.total_in_lhu = len(lhu_students)
            logger.info(f"✓ Fetched {result.total_in_lhu} students from LHU MySQL")

            if result.total_in_lhu == 0:
                result.success = True
                result.message = "Không có sinh viên nào trong LHU database"
                return result

            # Step 2: Get TLMS users (all or filtered by user_ids)
            logger.info("Step 2: Fetching users from TLMS PostgreSQL...")
            if user_ids:
                logger.info(f"Syncing specific users: {user_ids}")
                stmt = select(User).where(User.id.in_(user_ids))
            else:
                stmt = select(User)
            
            logger.info(f"DB Session type: {type(db_session)}")
            logger.info(f"Statement: {stmt}")
            
            try:
                query_result = await db_session.execute(stmt)
                logger.info(f"✓ Execute succeeded, result type: {type(query_result)}")
                tlms_users = query_result.scalars().all()
                logger.info(f"✓ Scalars all succeeded, got {len(tlms_users)} users")
            except Exception as db_err:
                logger.error(f"Database error: {type(db_err).__name__}: {str(db_err)}")
                import traceback
                logger.error(traceback.format_exc())
                raise
            
            logger.info(f"Found {len(tlms_users)} users in TLMS PostgreSQL")

            # Step 3: Create lookup maps for faster matching
            # ONLY include users that were requested (if user_ids provided)
            email_to_user = {}
            phone_to_user = {}

            logger.info("Building email and phone lookup maps...")
            for user in tlms_users:
                if user.email:
                    email_to_user[user.email.lower()] = user
                if user.phone:
                    # Normalize phone: remove spaces, dashes, ensure +84 or 0
                    phone_normalized = self._normalize_phone(user.phone)
                    if phone_normalized:
                        phone_to_user[phone_normalized] = user

            logger.info(f"Email map: {len(email_to_user)} entries, Phone map: {len(phone_to_user)} entries")

            # Step 4: Match and update
            updated_count = 0
            skipped_count = 0
            error_count = 0
            errors = []
            matched_by_email = 0
            matched_by_phone = 0
            
            logger.info("Starting matching process...")

            for i, student in enumerate(lhu_students):
                try:
                    matched_user = None
                    match_method = None

                    # Try match by phone FIRST (phone is unique identifier)
                    if student.phone:
                        phone_normalized = self._normalize_phone(student.phone)
                        if phone_normalized:
                            matched_user = phone_to_user.get(phone_normalized)
                            if matched_user:
                                match_method = "phone"
                                matched_by_phone += 1

                    # Try match by email if no phone match
                    if not matched_user and student.email:
                        matched_user = email_to_user.get(student.email.lower())
                        if matched_user:
                            match_method = "email"
                            matched_by_email += 1

                    # Update if matched and has uid
                    if matched_user and student.uid:
                        needs_update = False
                        
                        # Update student_id if missing or different
                        if not matched_user.student_id or matched_user.student_id != student.uid:
                            matched_user.student_id = student.uid
                            needs_update = True
                        
                        # Update phone if missing (from LHU)
                        if student.phone and not matched_user.phone:
                            matched_user.phone = student.phone
                            needs_update = True
                        
                        if needs_update:
                            updated_count += 1
                            logger.debug(
                                f"Updated {matched_user.email} with student_id: {student.uid}, phone: {student.phone} "
                                f"(matched by {match_method})"
                            )
                        else:
                            skipped_count += 1
                            logger.debug(
                                f"Skipped {matched_user.email} - already has student_id: {student.uid}"
                            )
                    else:
                        skipped_count += 1
                        if not student.uid:
                            logger.debug(f"Skipped - no UID for: {student.email or student.phone}")
                        else:
                            logger.debug(
                                f"Skipped - no match for: {student.email or student.phone}"
                            )

                except Exception as e:
                    error_count += 1
                    error_msg = f"Error processing student {student.uid}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                
                # Log progress every 10000 students
                if (i + 1) % 10000 == 0:
                    logger.info(f"Processed {i + 1}/{len(lhu_students)} students...")

            logger.info(f"Matching completed. Updated: {updated_count}, Skipped: {skipped_count}, Errors: {error_count}")
            logger.info("Committing changes to database...")

            # Step 5: Commit changes
            # For AsyncSession, we need to use run_sync() or await if it's async
            try:
                await db_session.commit()
            except TypeError:
                # Fallback for sync commit
                db_session.commit()

            result.success = True
            result.matched_by_email = matched_by_email
            result.matched_by_phone = matched_by_phone
            result.updated_count = updated_count
            result.skipped_count = skipped_count
            result.error_count = error_count
            result.errors = errors[:10]  # Only first 10 errors
            
            result.message = (
                f"Đồng bộ thành công: {updated_count} user được cập nhật mã sinh viên | "
                f"Match qua email: {matched_by_email} | Match qua phone: {matched_by_phone} | "
                f"Bỏ qua: {skipped_count} | Lỗi: {error_count}"
            )
            
            logger.info(result.message)

        except Exception as e:
            # Rollback - try async first, fallback to sync
            try:
                await db_session.rollback()
            except (TypeError, AttributeError):
                db_session.rollback()
            result.success = False
            result.message = f"Lỗi đồng bộ: {str(e)}"
            result.errors.append(str(e))
            logger.error(result.message)

        return result

    def _normalize_phone(self, phone: str) -> Optional[str]:
        """
        Normalize phone number for matching
        
        Examples:
            "0901234567" -> "0901234567"
            "+84901234567" -> "0901234567"
            "84901234567" -> "0901234567"
            "090-123-4567" -> "0901234567"
        """
        if not phone:
            return None
        
        # Remove spaces, dashes, dots
        cleaned = ''.join(c for c in phone if c.isdigit())
        
        # Convert +84 or 84 prefix to 0
        if cleaned.startswith('+84'):
            cleaned = '0' + cleaned[3:]
        elif cleaned.startswith('84'):
            cleaned = '0' + cleaned[2:]
        
        # Must be at least 10 digits
        if len(cleaned) < 10:
            return None
        
        return cleaned


# Singleton instance
lhu_student_sync_service = LHUStudentSyncService()
