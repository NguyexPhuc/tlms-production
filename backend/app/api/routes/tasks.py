"""
Task Routes - API endpoints for task management
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.api.deps import get_current_user, require_admin, require_mentor
from app.models.user import User
from app.models.task import TaskType, TaskStatus, UserTask
from app.models.schedule import Attendance, Shift as ScheduleShift
from app.services.task import task_service
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    TaskStatsResponse,
    TaskDetailResponse,
    UserTaskStart,
    UserTaskSubmit,
    UserTaskReview,
    UserTaskResponse,
    UserTaskListResponse
)
from app.models.schedule import Attendance, Shift as ScheduleShift

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ============================================
# Task Management (Admin)
# ============================================

@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo task mới (Admin/Mentor)",
    dependencies=[Depends(require_mentor)]
)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Tạo task mới (Core hoặc Bounty) - Mentor/Admin"""
    task = await task_service.create_task(db, task_data, current_user)
    return task


@router.get(
    "",
    response_model=TaskListResponse,
    summary="Danh sách tasks"
)
async def list_tasks(
    task_type: Optional[TaskType] = Query(None, description="Filter by task type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy danh sách tasks với filter và pagination"""
    tasks, total = await task_service.list_tasks(
        db, task_type, is_active, page, page_size
    )

    # Build response with creator info
    tasks_data = []
    for task in tasks:
        task_dict = {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'type': task.type,
            'scope': task.scope,
            'difficulty': task.difficulty,
            'min_level_required': task.min_level_required,
            'max_participants': task.max_participants,
            'prerequisite_task_ids': task.prerequisite_task_ids,
            'xp_reward': task.xp_reward,
            'skill_tags': task.skill_tags,
            'instructions': task.instructions,
            'reference_links': task.reference_links,
            'is_active': task.is_active,
            'order_index': task.order_index,
            'created_at': task.created_at,
            'updated_at': task.updated_at,
            'creator_id': task.creator_id,
            'creator_name': task.creator.full_name if task.creator else None,
        }
        tasks_data.append(TaskResponse(**task_dict))

    return TaskListResponse(
        tasks=tasks_data,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get(
    "/stats",
    response_model=TaskStatsResponse,
    summary="Thống kê tasks"
)
async def get_task_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy thống kê về tasks"""
    stats = await task_service.get_task_stats(db)
    return TaskStatsResponse(**stats)





# ============================================
# User Task Progress
# ============================================

@router.get(
    "/available/me",
    response_model=TaskListResponse,
    summary="Tasks có thể làm"
)
async def get_available_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy danh sách tasks mà user có thể làm (dựa trên level và prerequisites)"""
    tasks = await task_service.get_user_available_tasks(db, current_user)

    # Build response with creator info
    tasks_data = []
    for task in tasks:
        task_dict = {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'type': task.type,
            'scope': task.scope,
            'difficulty': task.difficulty,
            'min_level_required': task.min_level_required,
            'max_participants': task.max_participants,
            'prerequisite_task_ids': task.prerequisite_task_ids,
            'xp_reward': task.xp_reward,
            'skill_tags': task.skill_tags,
            'instructions': task.instructions,
            'reference_links': task.reference_links,
            'is_active': task.is_active,
            'order_index': task.order_index,
            'created_at': task.created_at,
            'updated_at': task.updated_at,
            'creator_id': task.creator_id,
            'creator_name': task.creator.full_name if task.creator else None,
        }
        tasks_data.append(TaskResponse(**task_dict))

    return TaskListResponse(
        tasks=tasks_data,
        total=len(tasks),
        page=1,
        page_size=len(tasks)
    )


@router.post(
    "/start",
    response_model=UserTaskResponse,
    summary="Bắt đầu làm task"
)
async def start_task(
    data: UserTaskStart,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """User claim/start một task"""
    user_task = await task_service.start_task(db, current_user, data.task_id)
    return UserTaskResponse.model_validate(user_task)


@router.post(
    "/start-assigned/{user_task_id:uuid}",
    response_model=UserTaskResponse,
    summary="Bắt đầu assignment đã được giao"
)
async def start_assigned_task(
    user_task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """User starts a pre-assigned task, including Daily Task."""
    user_task = await task_service.start_assigned_task(db, current_user, user_task_id)
    return UserTaskResponse.model_validate(user_task)


@router.get(
    "/my-tasks",
    response_model=UserTaskListResponse,
    summary="Tasks của tôi"
)
async def get_my_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy danh sách tasks mà user đang làm/đã làm"""
    user_tasks, counts = await task_service.get_user_tasks(db, current_user, status_filter)

    # Build response with creator info
    tasks_data = []
    for ut in user_tasks:
        creator_name = None
        if ut.task.creator:
            creator_name = ut.task.creator.full_name or ut.task.creator.email
        
        task_dict = {
            'id': ut.id,
            'user_id': ut.user_id,
            'user_email': None,
            'user_full_name': None,
            'task_id': ut.task_id,
            'task': {
                'id': ut.task.id,
                'title': ut.task.title,
                'description': ut.task.description,
                'type': ut.task.type,
                'scope': ut.task.scope,
                'difficulty': ut.task.difficulty,
                'min_level_required': ut.task.min_level_required,
                'max_participants': ut.task.max_participants,
                'prerequisite_task_ids': ut.task.prerequisite_task_ids,
                'xp_reward': ut.task.xp_reward,
                'skill_tags': ut.task.skill_tags,
                'instructions': ut.task.instructions,
                'reference_links': ut.task.reference_links,
                'is_active': ut.task.is_active,
                'order_index': ut.task.order_index,
                'created_at': ut.task.created_at,
                'updated_at': ut.task.updated_at,
                'creator_id': ut.task.creator_id,
                'creator_name': creator_name,
            },
            'status': ut.status,
            'proof_link': ut.proof_link,
            'submission_notes': ut.submission_notes,
            'submitted_at': ut.submitted_at,
            'reviewer_id': ut.reviewer_id,
            'mentor_comment': ut.mentor_comment,
            'reviewed_at': ut.reviewed_at,
            'xp_earned': ut.xp_earned,
            'started_at': ut.started_at,
            'completed_at': ut.completed_at,
            'created_at': ut.created_at,
            'updated_at': ut.updated_at,
        }
        tasks_data.append(UserTaskResponse(**task_dict))

    return UserTaskListResponse(
        tasks=tasks_data,
        total=counts['total'],
        completed_count=counts['completed'],
        pending_count=counts['submitted'],
        in_progress_count=counts['in_progress']
    )


@router.get(
    "/user/{user_id}",
    response_model=UserTaskListResponse,
    summary="Tasks của user khác (Admin/Mentor)",
    dependencies=[Depends(require_mentor)]
)
async def get_user_tasks(
    user_id: UUID,
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy danh sách tasks của user khác - Admin/Mentor only"""
    # Get target user
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise NotFoundException("User not found")

    user_tasks, counts = await task_service.get_user_tasks(db, target_user, status_filter)

    # Build response with creator info
    tasks_data = []
    for ut in user_tasks:
        task_dict = {
            'id': ut.id,
            'user_id': ut.user_id,
            'user_email': None,
            'user_full_name': None,
            'task_id': ut.task_id,
            'task': {
                'id': ut.task.id,
                'title': ut.task.title,
                'description': ut.task.description,
                'type': ut.task.type,
                'scope': ut.task.scope,
                'difficulty': ut.task.difficulty,
                'min_level_required': ut.task.min_level_required,
                'max_participants': ut.task.max_participants,
                'prerequisite_task_ids': ut.task.prerequisite_task_ids,
                'xp_reward': ut.task.xp_reward,
                'skill_tags': ut.task.skill_tags,
                'instructions': ut.task.instructions,
                'reference_links': ut.task.reference_links,
                'is_active': ut.task.is_active,
                'order_index': ut.task.order_index,
                'created_at': ut.task.created_at,
                'updated_at': ut.task.updated_at,
                'creator_id': ut.task.creator_id,
                'creator_name': ut.task.creator.full_name if ut.task.creator else None,
            },
            'status': ut.status,
            'proof_link': ut.proof_link,
            'submission_notes': ut.submission_notes,
            'submitted_at': ut.submitted_at,
            'reviewer_id': ut.reviewer_id,
            'mentor_comment': ut.mentor_comment,
            'reviewed_at': ut.reviewed_at,
            'xp_earned': ut.xp_earned,
            'started_at': ut.started_at,
            'completed_at': ut.completed_at,
            'created_at': ut.created_at,
            'updated_at': ut.updated_at,
        }
        tasks_data.append(UserTaskResponse(**task_dict))

    return UserTaskListResponse(
        tasks=tasks_data,
        total=counts['total'],
        completed_count=counts['completed'],
        pending_count=counts['submitted'],
        in_progress_count=counts['in_progress']
    )


@router.post(
    "/submit/{user_task_id}",
    response_model=UserTaskResponse,
    summary="Nộp bài task"
)
async def submit_task(
    user_task_id: UUID,
    data: UserTaskSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """User nộp bài task để mentor review"""
    user_task = await task_service.submit_task(
        db,
        current_user,
        user_task_id,
        data.proof_link,
        data.submission_notes,
        data.completion_percentage,
        data.evidence_links
    )
    
    return UserTaskResponse.model_validate(user_task)


# ============================================
# Mentor Review
# ============================================

@router.get(
    "/pending-reviews",
    response_model=UserTaskListResponse,
    summary="Tasks chờ review (Mentor)",
    dependencies=[Depends(require_mentor)]
)
async def get_pending_reviews(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy danh sách tasks đang chờ mentor review"""
    user_tasks = await task_service.get_pending_reviews(db, current_user)

    tasks_data = []
    for ut in user_tasks:
        task_data = {
            'id': ut.id,
            'user_id': ut.user_id,
            'user_email': ut.user.email if ut.user else None,
            'user_full_name': ut.user.full_name if ut.user else None,
            'task_id': ut.task_id,
            'task': ut.task,
            'status': ut.status,
            'proof_link': ut.proof_link,
            'submission_notes': ut.submission_notes,
            'submitted_at': ut.submitted_at,
            'reviewer_id': ut.reviewer_id,
            'mentor_comment': ut.mentor_comment,
            'reviewed_at': ut.reviewed_at,
            'xp_earned': ut.xp_earned,
            'started_at': ut.started_at,
            'completed_at': ut.completed_at,
            'created_at': ut.created_at,
            'updated_at': ut.updated_at,
        }
        tasks_data.append(UserTaskResponse(**task_data))

    return UserTaskListResponse(
        tasks=tasks_data,
        total=len(user_tasks),
        completed_count=0,
        pending_count=len(user_tasks),
        in_progress_count=0
    )


@router.post(
    "/review/{user_task_id}",
    response_model=UserTaskResponse,
    summary="Review task (Mentor)",
    dependencies=[Depends(require_mentor)]
)
async def review_task(
    user_task_id: UUID,
    data: UserTaskReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mentor review và approve/reject task"""
    approved = data.status == TaskStatus.APPROVED
    
    user_task = await task_service.review_task(
        db,
        current_user,
        user_task_id,
        approved,
        data.mentor_comment,
        data.manager_score,
        data.final_score
    )
    
    return UserTaskResponse.model_validate(user_task)


# ============================================
# CRUD for Task (moved to bottom to avoid path collision)
# ============================================

@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Chi tiết task"
)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy thông tin chi tiết của một task"""
    task = await task_service.get_task_by_id(db, task_id)
    
    task_dict = {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'type': task.type,
        'scope': task.scope,
        'difficulty': task.difficulty,
        'min_level_required': task.min_level_required,
        'max_participants': task.max_participants,
        'prerequisite_task_ids': task.prerequisite_task_ids,
        'xp_reward': task.xp_reward,
        'skill_tags': task.skill_tags,
        'instructions': task.instructions,
        'reference_links': task.reference_links,
        'is_active': task.is_active,
        'order_index': task.order_index,
        'created_at': task.created_at,
        'updated_at': task.updated_at,
        'creator_id': task.creator_id,
        'creator_name': task.creator.full_name if task.creator else None,
    }
    return TaskResponse(**task_dict)


@router.get(
    "/{task_id}/details",
    response_model=TaskDetailResponse,
    summary="Chi tiết task với người tham gia (Mentor/Admin)",
    dependencies=[Depends(require_mentor)]
)
async def get_task_details(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy thông tin chi tiết của task kèm danh sách người tham gia - Mentor/Admin only"""
    task_data = await task_service.get_task_detail_with_participants(db, task_id)
    return TaskDetailResponse.model_validate(task_data)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Cập nhật task (Admin)",
    dependencies=[Depends(require_admin)]
)
async def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cập nhật thông tin task - Admin only"""
    task = await task_service.update_task(db, task_id, task_data, current_user)
    return TaskResponse.model_validate(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa task (Admin/Mentor)",
    dependencies=[Depends(require_mentor)]
)
async def delete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Xóa task - Admin/Mentor only"""
    await task_service.delete_task(db, task_id, current_user)


# ============================================
# Dashboard & Statistics
# ============================================

from pydantic import BaseModel
from datetime import date, datetime, timedelta

class UserStatsResponse(BaseModel):
    """User statistics for dashboard"""
    user_id: str
    user_name: str
    user_email: str
    # All-time stats
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    submitted_tasks: int
    total_checkins: int
    morning_shifts: int
    afternoon_shifts: int
    evening_shifts: int
    total_hours: float
    # Weekly stats
    weekly_tasks: int
    weekly_completed_tasks: int
    weekly_checkins: int
    weekly_morning_shifts: int
    weekly_afternoon_shifts: int
    weekly_evening_shifts: int
    weekly_hours: float

@router.get(
    "/user-stats/{user_id}",
    response_model=UserStatsResponse,
    summary="Thống kê user (Admin/Mentor)",
    dependencies=[Depends(require_mentor)]
)
async def get_user_stats(
    user_id: UUID,
    week_start: Optional[str] = Query(None, description="Week start date (YYYY-MM-DD), defaults to current week"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy thống kê chi tiết của user - Admin/Mentor only"""
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise NotFoundException("User not found")

    # Calculate week start (Monday)
    if week_start:
        week_start_date = datetime.strptime(week_start, '%Y-%m-%d').date()
    else:
        # Get current week start (Monday)
        week_start_date = date.today() - timedelta(days=date.today().weekday())

    week_end_date = week_start_date + timedelta(days=6)

    # Convert to datetime for task comparison (use start/end of day)
    week_start_dt = datetime.combine(week_start_date, datetime.min.time())
    week_end_dt = datetime.combine(week_end_date, datetime.max.time())
    
    logger.info(f"Getting stats for user {user_id}, week: {week_start_date} to {week_end_date}")
    
    # Get all-time task stats
    task_result = await db.execute(
        select(
            func.count(UserTask.id).label('total'),
            func.sum(case((UserTask.status == TaskStatus.COMPLETED, 1), else_=0)).label('completed'),
            func.sum(case((UserTask.status == TaskStatus.IN_PROGRESS, 1), else_=0)).label('in_progress'),
            func.sum(case((UserTask.status == TaskStatus.SUBMITTED, 1), else_=0)).label('submitted')
        ).where(UserTask.user_id == user_id)
    )
    task_stats = task_result.first()
    
    # Get weekly task stats
    weekly_task_result = await db.execute(
        select(
            func.count(UserTask.id).label('total'),
            func.sum(case((UserTask.status == TaskStatus.COMPLETED, 1), else_=0)).label('completed')
        ).where(
            UserTask.user_id == user_id,
            UserTask.created_at >= week_start_dt,
            UserTask.created_at <= week_end_dt
        )
    )
    weekly_task_stats = weekly_task_result.first()
    
    # Get all-time attendance stats
    attendance_result = await db.execute(
        select(
            func.count(Attendance.id).label('total'),
            func.sum(case((Attendance.shift == ScheduleShift.MORNING, 1), else_=0)).label('morning'),
            func.sum(case((Attendance.shift == ScheduleShift.AFTERNOON, 1), else_=0)).label('afternoon'),
            func.sum(case((Attendance.shift == ScheduleShift.EVENING, 1), else_=0)).label('evening')
        ).where(Attendance.user_id == user_id)
    )
    attendance_stats = attendance_result.first()
    
    # Get weekly attendance stats
    weekly_attendance_result = await db.execute(
        select(
            func.count(Attendance.id).label('total'),
            func.sum(case((Attendance.shift == ScheduleShift.MORNING, 1), else_=0)).label('morning'),
            func.sum(case((Attendance.shift == ScheduleShift.AFTERNOON, 1), else_=0)).label('afternoon'),
            func.sum(case((Attendance.shift == ScheduleShift.EVENING, 1), else_=0)).label('evening')
        ).where(
            Attendance.user_id == user_id,
            Attendance.work_date >= week_start_date,
            Attendance.work_date <= week_end_date
        )
    )
    weekly_attendance_stats = weekly_attendance_result.first()
    
    # Calculate total hours (4 hours per shift)
    total_hours = (attendance_stats.total or 0) * 4.0
    weekly_hours = (weekly_attendance_stats.total or 0) * 4.0
    
    return UserStatsResponse(
        user_id=str(target_user.id),
        user_name=target_user.full_name or target_user.email,
        user_email=target_user.email,
        total_tasks=task_stats.total or 0,
        completed_tasks=task_stats.completed or 0,
        in_progress_tasks=task_stats.in_progress or 0,
        submitted_tasks=task_stats.submitted or 0,
        total_checkins=attendance_stats.total or 0,
        morning_shifts=attendance_stats.morning or 0,
        afternoon_shifts=attendance_stats.afternoon or 0,
        evening_shifts=attendance_stats.evening or 0,
        total_hours=total_hours,
        weekly_tasks=weekly_task_stats.total or 0,
        weekly_completed_tasks=weekly_task_stats.completed or 0,
        weekly_checkins=weekly_attendance_stats.total or 0,
        weekly_morning_shifts=weekly_attendance_stats.morning or 0,
        weekly_afternoon_shifts=weekly_attendance_stats.afternoon or 0,
        weekly_evening_shifts=weekly_attendance_stats.evening or 0,
        weekly_hours=weekly_hours
    )
