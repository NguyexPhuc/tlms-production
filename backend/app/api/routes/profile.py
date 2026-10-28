"""
Profile Routes - API endpoints for user profile management
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_user, require_admin, require_mentor
from app.models.user import User
from app.services.profile import profile_service
from app.schemas.profile import (
    ProfileEvidenceCreate,
    ProfileEvidenceUpdate,
    ProfileEvidenceVerify,
    ProfileEvidenceOut,
    ProfileStats,
    ProfileResponse,
    AutoScheduleRequest,
    AutoScheduleResult
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["Profile"])


# ============================================
# Profile Evidence Management
# ============================================

@router.post(
    "/evidence",
    response_model=ProfileEvidenceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm minh chứng vào profile"
)
async def create_evidence(
    evidence_data: ProfileEvidenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Thêm minh chứng (evidence) vào profile
    - Có thể link với task hoặc tự do
    - Thêm links, mô tả, tags
    """
    evidence = await profile_service.create_evidence(db, current_user, evidence_data)
    return ProfileEvidenceOut.model_validate(evidence)


@router.get(
    "/evidence",
    response_model=List[ProfileEvidenceOut],
    summary="Lấy danh sách minh chứng"
)
async def get_evidence(
    include_pending: bool = Query(True, description="Include pending evidence"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy tất cả minh chứng của user"""
    evidence_list = await profile_service.get_user_evidence(db, current_user, include_pending)
    return [ProfileEvidenceOut.model_validate(e) for e in evidence_list]


@router.patch(
    "/evidence/{evidence_id}",
    response_model=ProfileEvidenceOut,
    summary="Cập nhật minh chứng"
)
async def update_evidence(
    evidence_id: UUID,
    evidence_data: ProfileEvidenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cập nhật minh chứng của user"""
    evidence = await profile_service.update_evidence(db, current_user, evidence_id, evidence_data)
    return ProfileEvidenceOut.model_validate(evidence)


@router.delete(
    "/evidence/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa minh chứng"
)
async def delete_evidence(
    evidence_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Xóa minh chứng"""
    await profile_service.delete_evidence(db, current_user, evidence_id)


@router.post(
    "/evidence/{evidence_id}/verify",
    response_model=ProfileEvidenceOut,
    summary="Xác nhận minh chứng (Mentor/Admin)",
    dependencies=[Depends(require_mentor)]
)
async def verify_evidence(
    evidence_id: UUID,
    verify_data: ProfileEvidenceVerify,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Xác nhận minh chứng (Mentor/Admin only)
    - Approve/Reject
    - Mark as featured
    """
    evidence = await profile_service.verify_evidence(db, current_user, evidence_id, verify_data)
    return ProfileEvidenceOut.model_validate(evidence)


# ============================================
# Profile Statistics
# ============================================

@router.get(
    "/stats",
    response_model=ProfileStats,
    summary="Lấy thống kê profile"
)
async def get_profile_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy thống kê chi tiết của profile:
    - Work schedule stats (giờ làm, attendance rate)
    - Task stats (tasks hoàn thành, XP, level)
    - Achievements (evidence, skill tags, discipline score)
    """
    stats = await profile_service.get_profile_stats(db, current_user)
    return stats


@router.get(
    "/me",
    response_model=ProfileResponse,
    summary="Lấy profile đầy đủ"
)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy profile đầy đủ của user:
    - User info
    - Statistics
    - Evidence list
    - Recent tasks
    - Upcoming schedules
    """
    profile = await profile_service.get_complete_profile(db, current_user)
    return profile


@router.get(
    "/user/{user_id}",
    response_model=ProfileResponse,
    summary="Xem profile user khác (Admin/Mentor)",
    dependencies=[Depends(require_mentor)]
)
async def get_user_profile(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Xem profile của user khác (Mentor/Admin only)"""
    from app.models.user import User
    from sqlalchemy import select
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("User not found")
    
    profile = await profile_service.get_complete_profile(db, user)
    return profile


# ============================================
# Auto-Schedule Feature
# ============================================

@router.post(
    "/auto-schedule",
    response_model=AutoScheduleResult,
    summary="Tự động đăng ký lịch làm dựa trên lịch học"
)
async def auto_register_schedule(
    request: AutoScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Tự động đăng ký lịch làm để đủ 8h/ngày
    - Dựa trên lịch học từ LHU
    - Tự động chọn các ca trống
    - Tránh conflict với lịch học
    """
    result = await profile_service.auto_register_work_schedule(db, current_user, request)
    return result
