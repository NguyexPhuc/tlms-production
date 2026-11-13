"""
Profile Routes - API endpoints for user profile management
"""
import asyncio
import io
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, File, status, Query, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import BadRequestException, NotFoundException
from app.api.deps import get_current_user, require_admin, require_mentor
from app.models.user import User
from app.services.object_storage import object_storage
from app.services.profile import profile_service
from app.schemas.profile import (
    AvatarResponse,
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
settings = get_settings()

AVATAR_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
AVATAR_MAX_PIXELS = 25_000_000
AVATAR_SIZE = (512, 512)


def _prepare_avatar_image(content: bytes) -> bytes:
    """Validate, orient, resize and remove metadata from an avatar image."""
    try:
        with Image.open(io.BytesIO(content)) as source:
            source.load()
            if source.width * source.height > AVATAR_MAX_PIXELS:
                raise BadRequestException("Ảnh đại diện có độ phân giải quá lớn")
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail(AVATAR_SIZE, Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=88, optimize=True)
            return output.getvalue()
    except BadRequestException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise BadRequestException("File ảnh đại diện không hợp lệ") from exc


@router.post(
    "/avatar",
    response_model=AvatarResponse,
    summary="Thay ảnh đại diện của tôi",
)
async def upload_my_avatar(
    avatar: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if avatar.content_type not in AVATAR_CONTENT_TYPES:
        raise BadRequestException("Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP")

    content = await avatar.read()
    if not content:
        raise BadRequestException("File ảnh đại diện rỗng")
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise BadRequestException("Ảnh đại diện vượt quá dung lượng cho phép")

    normalized = await asyncio.to_thread(_prepare_avatar_image, content)
    relative_key = f"avatars/{current_user.id}.jpg"
    await asyncio.to_thread(
        object_storage.put_upload,
        relative_key,
        normalized,
        "image/jpeg",
    )

    current_user.avatar_url = f"/api/v1/profile/avatar/{current_user.id}?v={uuid4().hex[:12]}"
    await db.commit()
    await db.refresh(current_user)
    logger.info("Avatar updated for user %s", current_user.email)
    return AvatarResponse(avatar_url=current_user.avatar_url)


@router.get(
    "/avatar/{user_id:uuid}",
    summary="Xem ảnh đại diện",
)
async def get_avatar(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user or not user.avatar_url:
        raise NotFoundException("Không tìm thấy ảnh đại diện")

    relative_key = f"avatars/{user_id}.jpg"
    try:
        stored = await asyncio.to_thread(object_storage.read_upload, relative_key)
    except (FileNotFoundError, ValueError) as exc:
        raise NotFoundException("Không tìm thấy ảnh đại diện") from exc

    return StreamingResponse(
        io.BytesIO(stored.content),
        media_type=stored.content_type,
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Disposition": 'inline; filename="avatar.jpg"',
        },
    )


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
