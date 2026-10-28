"""
User Management Routes - Admin only
"""
import re
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, any_, case
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User, UserRole, UserStatus, MemberLevel
from app.schemas.user import (
    UserResponse,
    UserListResponse,
    UserRolesUpdate,
    UserStatusUpdate,
    UserMemberLevelUpdate
)
from app.api.deps import get_current_user
from app.api.rbac import get_admin_user
from app.services.notification import notification_service

router = APIRouter(prefix="/users", tags=["User Management"])


def validate_role_policy(roles: List[str]) -> List[str]:
    """Normalize roles and enforce the single-role account policy."""
    normalized_roles = list(dict.fromkeys(roles))

    if len(normalized_roles) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mỗi tài khoản phải có đúng một quyền"
        )

    return normalized_roles


def user_to_response(user: User) -> UserResponse:
    """Convert User model to UserResponse"""
    # Use the model rule so learning accounts always level by XP.
    display_level = user.calculate_level()

    return UserResponse(
        id=str(user.id),
        s4h_user_id=user.s4h_user_id,
        email=user.email,
        student_id=user.student_id,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        roles=user.roles or ['candidate'],
        primary_role=user.primary_role,
        status=user.status.value if hasattr(user.status, 'value') else user.status,
        current_xp=user.current_xp,
        level=display_level,
        discipline_score=float(user.discipline_score),
        reliability_score=float(user.reliability_score),
        member_score=float(user.member_score),
        promotion_progress=float(user.promotion_progress),
        member_level=user.member_level,
        core_task_progress=user.core_task_progress,
        is_ready_to_promote=user.is_ready_to_promote,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at
    )


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user's profile"""
    return user_to_response(current_user)


@router.get("/{user_id:uuid}", response_model=UserResponse)
async def get_user_profile(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get any user's profile (for viewing other users)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_to_response(user)


from pydantic import BaseModel, field_validator
class StudentIdUpdate(BaseModel):
    student_id: str

    @field_validator("student_id")
    @classmethod
    def validate_student_id(cls, value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9]{6,20}", normalized):
            raise ValueError("MSSV phải gồm 6-20 chữ cái hoặc chữ số")
        return normalized

@router.put("/me/student-id", response_model=UserResponse)
async def update_student_id(
    data: StudentIdUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update student ID for schedule sync"""
    owner = (
        await db.execute(
            select(User).where(
                User.student_id == data.student_id,
                User.id != current_user.id,
            )
        )
    ).scalar_one_or_none()

    current_is_learner = current_user.primary_role in {
        UserRole.CANDIDATE.value,
        UserRole.MEMBER.value,
    }
    owner_is_management_only = owner and owner.primary_role in {
        UserRole.MENTOR.value,
        UserRole.ADMIN.value,
    }

    if owner and current_is_learner and owner_is_management_only:
        # Management accounts do not consume student schedules. Reclaiming a
        # stale MSSV here fixes data imported into the wrong account.
        owner.student_id = None
        # Flush first so PostgreSQL releases the unique value before the
        # current learner receives it in the same transaction.
        await db.flush()
    elif owner:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MSSV này đang được sử dụng bởi một tài khoản học tập khác",
        )

    current_user.student_id = data.student_id
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MSSV này đã được sử dụng",
        ) from exc
    await db.refresh(current_user)
    return user_to_response(current_user)


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=1000, description="Items per page"),
    role: Optional[str] = Query(None, description="Filter by role"),
    user_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all users with pagination and filters
    Admin and Mentor only
    """
    # Check permission
    if not (current_user.is_admin() or current_user.is_mentor()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin and mentor can access user list"
        )
    # Build query
    query = select(User)
    count_query = select(func.count(User.id))
    
    # Apply filters
    if role:
        # Check if role value is valid
        valid_roles = [r.value for r in UserRole]
        if role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}. Must be one of: {valid_roles}"
            )
        # Filter users who have this role in their roles array
        query = query.where(User.roles.any(role))
        count_query = count_query.where(User.roles.any(role))
    
    if user_status:
        try:
            status_enum = UserStatus(user_status)
            query = query.where(User.status == status_enum)
            count_query = count_query.where(User.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {user_status}. Must be one of: {[s.value for s in UserStatus]}"
            )
    
    if search:
        # Split search query into words for smarter search
        search_words = search.strip().split()
        if search_words:
            # Build conditions for each word
            word_conditions = []
            relevance_cases = []
            
            for word in search_words:
                search_filter = f"%{word}%"
                
                # Build OR condition for this word across all fields
                word_conditions.append(
                    (User.first_name.ilike(search_filter)) |
                    (User.last_name.ilike(search_filter)) |
                    (User.email.ilike(search_filter)) |
                    (User.student_id.ilike(search_filter)) |
                    (User.phone.ilike(search_filter))  # Search by phone too
                )
                
                # Build relevance scoring for this word
                # Higher score for matches in more important fields
                relevance_cases.append(
                    case((User.first_name.ilike(search_filter), 3), else_=0) +
                    case((User.last_name.ilike(search_filter), 3), else_=0) +
                    case((User.email.ilike(search_filter), 2), else_=0) +
                    case((User.student_id.ilike(search_filter), 2), else_=0) +
                    case((User.phone.ilike(search_filter), 1), else_=0)
                )
            
            # Combine all word conditions with AND (all words must match)
            from sqlalchemy import and_, desc
            combined_filter = and_(*word_conditions) if len(word_conditions) > 1 else word_conditions[0]
            
            # Add relevance score to query
            total_relevance = sum(relevance_cases)
            query = query.add_columns(total_relevance.label('relevance'))
            query = query.where(combined_filter)
            count_query = count_query.where(combined_filter)
            
            # Order by relevance (highest first), then by created_at
            query = query.order_by(desc('relevance'), User.created_at.desc())

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size
    
    return UserListResponse(
        users=[user_to_response(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/check-admin-exists")
async def check_admin_exists(
    db: AsyncSession = Depends(get_db)
):
    """
    Check if any admin exists in the system
    Public endpoint - used to show/hide "Become First Admin" button
    """
    # Check if any user has 'admin' in their roles array
    result = await db.execute(
        select(func.count(User.id)).where(User.roles.any('admin'))
    )
    admin_count = result.scalar()
    
    return {
        "has_admin": admin_count > 0
    }


async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)  # Admin only
):
    """
    Get user details by ID
    Admin only
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )
    
    return user_to_response(user)


@router.patch("/{user_id:uuid}/roles", response_model=UserResponse)
async def update_user_roles(
    user_id: UUID,
    roles_update: UserRolesUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)  # Admin only
):
    """
    Update the user's single role.
    Admin only
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )
    
    # Validate all roles
    valid_roles = [r.value for r in UserRole]
    for role in roles_update.roles:
        if role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}. Must be one of: {valid_roles}"
            )
    normalized_roles = validate_role_policy(roles_update.roles)
    
    # Ensure at least one role
    if not roles_update.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User phải có ít nhất một role"
        )
    
    # Prevent self-demotion from admin
    if user.id == admin_user.id and 'admin' not in normalized_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn không thể tự bỏ quyền Admin của chính mình"
        )
    
    # Update roles
    old_roles = user.roles
    user.roles = normalized_roles
    
    await db.commit()
    await db.refresh(user)
    
    print(f"[RBAC] User {user.email} roles changed: {old_roles} -> {normalized_roles} by {admin_user.email}")
    
    return user_to_response(user)


@router.patch("/{user_id:uuid}/status", response_model=UserResponse)
async def update_user_status(
    user_id: UUID,
    status_update: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)  # Admin only
):
    """
    Update user status (active, inactive, suspended)
    Admin only
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )
    
    # Validate status
    try:
        new_status = UserStatus(status_update.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status_update.status}. Must be one of: {[s.value for s in UserStatus]}"
        )
    
    # Prevent self-suspension
    if user.id == admin_user.id and new_status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn không thể tự suspend/inactive chính mình"
        )
    
    # Update status
    old_status = user.status
    user.status = new_status
    
    await db.commit()
    await db.refresh(user)
    
    print(f"[RBAC] User {user.email} status changed: {old_status.value} -> {new_status.value} by {admin_user.email}")
    
    return user_to_response(user)


@router.patch("/{user_id:uuid}/member-level", response_model=UserResponse)
async def update_user_member_level(
    user_id: UUID,
    level_update: UserMemberLevelUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """
    Update member development level.
    This is separate from RBAC roles and does not change login permissions.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )

    old_level = user.member_level
    user.member_level = level_update.member_level
    if user.member_level == MemberLevel.OFFICIAL:
        user.is_ready_to_promote = False
        user.promotion_progress = 0.0

    await notification_service.create_notification(
        db,
        user_id=user.id,
        event_type="MEMBER_LEVEL_CHANGED",
        title="Cấp thành viên đã được cập nhật",
        message=f"Cấp thành viên của bạn đã đổi từ {old_level.value} sang {user.member_level.value}.",
        actor_id=admin_user.id,
        payload={
            "old_member_level": old_level.value,
            "new_member_level": user.member_level.value,
        },
    )

    await db.commit()
    await db.refresh(user)

    print(f"[MEMBER_LEVEL] User {user.email}: {old_level.value} -> {user.member_level.value} by {admin_user.email}")

    return user_to_response(user)


@router.post("/set-first-admin", response_model=UserResponse)
async def set_first_admin(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Set the first admin when no admin exists
    This endpoint only works when there are no admins in the system
    """
    # Check if any admin exists
    result = await db.execute(
        select(func.count(User.id)).where(User.roles.any('admin'))
    )
    admin_count = result.scalar()
    
    if admin_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Đã có Admin trong hệ thống. Liên hệ Admin hiện tại để được cấp quyền."
        )
    
    # First admin is a management account, not a learning account.
    current_user.roles = [UserRole.ADMIN.value]
    current_user.level = 99
    await db.commit()
    await db.refresh(current_user)
    
    print(f"[RBAC] First admin set: {current_user.email}")
    
    return user_to_response(current_user)


@router.get("/stats/by-role")
async def get_user_stats_by_role(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """
    Get user statistics grouped by role
    Admin only
    """
    stats = {}
    
    for role in UserRole:
        result = await db.execute(
            select(func.count(User.id)).where(User.roles.any(role.value))
        )
        stats[role.value] = result.scalar()
    
    return {
        "by_role": stats,
        "total": sum(stats.values())
    }
