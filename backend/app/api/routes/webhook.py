"""
S4H Check-in Webhook - Receive attendance data from S4H system
"""
import logging
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import get_settings
from app.models.user import User
from app.models.schedule import Attendance, AttendanceStatus, Shift

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhooks"])

settings = get_settings()


class S4HCheckInWebhook(BaseModel):
    """Webhook payload from S4H check-in system"""
    id: str = Field(..., alias='_id')  # MongoDB _id
    qrCodeId: str
    userId: str  # S4H user ID
    date: str  # Format: "DD/MM/YYYY"
    shift: str  # "morning", "afternoon", or "evening"
    checkedInAt: str  # ISO format UTC+0
    checkedOutAt: Optional[str] = None  # ISO format UTC+0, null until checkout
    isLate: bool
    isBooking: bool
    userAgent: Optional[str] = ""
    ipAddress: Optional[str] = ""
    createdAt: str  # ISO format UTC+0
    updatedAt: str  # ISO format UTC+0

    class Config:
        populate_by_name = True


def utc_to_vietnam_time(utc_str: str) -> datetime:
    """Convert UTC+0 ISO string to Vietnam time (UTC+7) - returns naive datetime"""
    # Parse UTC time
    utc_time = datetime.fromisoformat(utc_str.replace('Z', '+00:00'))
    # Convert to Vietnam time (UTC+7)
    vietnam_time = utc_time + timedelta(hours=7)
    # Remove timezone info to store in DB (TIMESTAMP WITHOUT TIME ZONE)
    return vietnam_time.replace(tzinfo=None)


@router.post("/s4h/checkin")
async def receive_s4h_checkin(
    payload: S4HCheckInWebhook,
    x_api_key: str = Header(..., alias="X-API-Key", description="Required API key for authentication"),
    db: AsyncSession = Depends(get_db)
):
    """
    Receive check-in/check-out webhook from S4H system
    
    Security: Requires X-API-Key header for authentication
    """
    # Validate API Key
    if not settings.WEBHOOK_API_KEY:
        logger.error("WEBHOOK_API_KEY not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error"
        )
    
    if not hmac.compare_digest(x_api_key, settings.WEBHOOK_API_KEY):
        logger.warning(f"Invalid API key attempt: {x_api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    try:
        logger.info(f"Received S4H check-in webhook: user={payload.userId}, date={payload.date}, shift={payload.shift}")

        # Convert times to Vietnam timezone
        checked_in_vn = utc_to_vietnam_time(payload.checkedInAt)
        checked_out_vn = utc_to_vietnam_time(payload.checkedOutAt) if payload.checkedOutAt else None

        logger.info(f"Vietnam times: check_in={checked_in_vn}, check_out={checked_out_vn}")
        logger.info(f"MongoDB ID: {payload.id}, isBooking={payload.isBooking}")
        
        # Find user by S4H user ID
        stmt = select(User).where(User.s4h_user_id == payload.userId)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User not found for S4H ID: {payload.userId}")
            # Still return 200 to acknowledge receipt
            return {
                "success": True,
                "message": f"User not found for S4H ID: {payload.userId}",
                "user_created": False
            }
        
        # Check if this is a new date
        if user.last_attendance_date != payload.date:
            # New date - reset shift flags
            logger.info(f"New attendance date for user {user.email}: {payload.date}")
            user.last_attendance_date = payload.date
            user.morning_shift = False
            user.afternoon_shift = False
            user.evening_shift = False
            user.is_late_today = False

        # Update shift status
        if payload.shift == "morning":
            user.morning_shift = True
            logger.info(f"Set morning shift for user {user.email}")
        elif payload.shift == "afternoon":
            user.afternoon_shift = True
            logger.info(f"Set afternoon shift for user {user.email}")
        elif payload.shift == "evening":
            user.evening_shift = True
            logger.info(f"Set evening shift for user {user.email}")

        # Update late status
        if payload.isLate:
            user.is_late_today = True
            logger.info(f"User {user.email} was late today")

        # Mark record as updated
        user.updated_at = datetime.utcnow()

        # Create attendance record
        try:
            # Parse work_date from payload
            work_date = datetime.strptime(payload.date, '%d/%m/%Y').date()
            
            # Determine shift enum
            shift_enum = Shift.MORNING if payload.shift == "morning" else (
                Shift.AFTERNOON if payload.shift == "afternoon" else Shift.EVENING
            )
            
            # Check if attendance record already exists
            existing_stmt = select(Attendance).where(
                Attendance.user_id == user.id,
                Attendance.work_date == work_date,
                Attendance.shift == shift_enum
            )
            existing_result = await db.execute(existing_stmt)
            existing_attendance = existing_result.scalar_one_or_none()
            
            if not existing_attendance:
                # Calculate points
                discipline_points = 0
                bonus_points = 0
                
                # Rule 1: Check-in on time = +1 discipline point
                if not payload.isLate:
                    discipline_points = 1
                    logger.info(f"User {user.email} checked in on time: +1 discipline point")
                else:
                    discipline_points = -2
                    logger.info(f"User {user.email} checked in late: -2 discipline points")
                
                # Rule 2: Afternoon shift = +1 bonus point (encourage afternoon work)
                # Rule 2.1: Evening shift = +1 bonus point (encourage evening work)
                if payload.shift == "afternoon":
                    bonus_points = 1
                    logger.info(f"User {user.email} checked in for afternoon shift: +1 bonus point")
                elif payload.shift == "evening":
                    bonus_points = 1
                    logger.info(f"User {user.email} checked in for evening shift: +1 bonus point")
                
                # Rule 3: Check-in without booking (spontaneous) = +1 bonus point
                if not payload.isBooking:
                    bonus_points += 1
                    logger.info(f"User {user.email} checked in without booking: +1 bonus point")
                
                # Update user's discipline score
                user.discipline_score = min(100.0, max(0.0, user.discipline_score + discipline_points))
                logger.info(f"User {user.email} discipline score: {user.discipline_score}")
                
                # Create new attendance record
                attendance = Attendance(
                    user_id=user.id,
                    work_date=work_date,
                    shift=shift_enum,
                    status=AttendanceStatus.PRESENT.value,
                    check_in_time=checked_in_vn,
                    check_out_time=checked_out_vn,
                    discipline_points_change=discipline_points,
                    bonus_points=bonus_points,
                    notes=f"Checked in via S4H{' (on time)' if not payload.isLate else ' (late)'}{' (afternoon)' if payload.shift == 'afternoon' else ''}{' (evening)' if payload.shift == 'evening' else ''}",
                    auto_reconciled=True,
                    reconciled_at=datetime.utcnow()
                )
                db.add(attendance)
                logger.info(f"Created attendance record for user {user.email}: date={payload.date}, shift={payload.shift}, discipline={discipline_points}, bonus={bonus_points}")
            else:
                logger.info(f"Attendance record already exists for user {user.email}: date={payload.date}, shift={payload.shift}")
        except Exception as e:
            logger.error(f"Error creating attendance record: {str(e)}", exc_info=True)
            # Don't fail the whole request, just log the error

        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Attendance updated for user {user.email}: morning={user.morning_shift}, afternoon={user.afternoon_shift}, late={user.is_late_today}")
        
        return {
            "success": True,
            "message": "Attendance recorded successfully",
            "user": {
                "email": user.email,
                "date": user.last_attendance_date,
                "morning_shift": user.morning_shift,
                "afternoon_shift": user.afternoon_shift,
                "evening_shift": user.evening_shift,
                "is_late": user.is_late_today
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing S4H webhook: {str(e)}", exc_info=True)
        # Return 200 to avoid retry from S4H system
        return {
            "success": False,
            "message": f"Error processing webhook: {str(e)}"
        }


@router.get("/s4h/checkin/test")
async def test_webhook():
    """Test endpoint to verify webhook is working"""
    return {
        "status": "ok",
        "message": "S4H check-in webhook is running",
        "timezone": "UTC+7 (Vietnam)"
    }
