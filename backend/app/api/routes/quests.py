"""Daily Quest routes."""
import asyncio
import io
import re
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.quest import DailyQuest
from app.models.user import User
from app.schemas.quest import (
    DailyQuestCompleteResponse,
    DailyQuestLimitResponse,
    DailyQuestListResponse,
    DailyQuestProofSubmitResponse,
    LimitQuestCreateRequest,
    LimitQuestCreateResponse,
)
from app.services.quest import daily_quest_service
from app.services.object_storage import object_storage


router = APIRouter(prefix="/quests", tags=["Daily Quests"])


async def _save_quest_proof_image(file: UploadFile | None) -> tuple[str | None, str | None]:
    if file is None:
        return None, None

    if not file.content_type or not file.content_type.startswith("image/"):
        raise BadRequestException("Chỉ hỗ trợ file ảnh minh chứng")

    settings = get_settings()
    content = await file.read()
    if not content:
        raise BadRequestException("File ảnh minh chứng rỗng")
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise BadRequestException("File ảnh minh chứng vượt quá dung lượng cho phép")

    original_name = file.filename or "proof-image"
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", original_name).strip("._") or "proof-image"
    filename = f"{uuid4()}_{safe_name}"
    relative_key = f"{settings.QUEST_PROOF_UPLOAD_DIR}/{filename}"
    image_url = await asyncio.to_thread(
        object_storage.put_upload,
        relative_key,
        content,
        file.content_type,
    )
    return image_url, original_name


@router.get("/daily", response_model=DailyQuestListResponse)
async def get_my_daily_quests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get or lazily generate the current user's Daily Quests."""
    return await daily_quest_service.get_daily_quests(db, current_user)


@router.get("/daily/limit", response_model=DailyQuestLimitResponse)
async def get_my_daily_quest_limit(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get today's Daily Quest limit and usage."""
    return await daily_quest_service.get_limit_info(db, current_user)


@router.get("/limit", response_model=DailyQuestListResponse)
async def get_my_limit_quests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current user's admin-created Limit Quests."""
    return await daily_quest_service.list_limit_quests(db, current_user)


@router.post("/limit", response_model=LimitQuestCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_limit_quest(
    data: LimitQuestCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Admin-only endpoint to create Limit Quests for coaching/offline meetings."""
    return await daily_quest_service.create_limit_quest(db, admin_user, data)


@router.post("/{quest_id:uuid}/submit", response_model=DailyQuestProofSubmitResponse)
async def submit_quest_proof(
    quest_id: UUID,
    proof_text: str | None = Form(None),
    proof_link: str | None = Form(None),
    proof_image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit quest proof for AI scoring."""
    image_url, image_name = await _save_quest_proof_image(proof_image)
    return await daily_quest_service.submit_quest_proof(
        db,
        quest_id,
        current_user,
        proof_text=proof_text,
        proof_link=proof_link,
        proof_image_url=image_url,
        proof_image_name=image_name,
    )


@router.get("/{quest_id:uuid}/proof-image")
async def download_quest_proof_image(
    quest_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Serve private proof images only to the owner, mentors, or admins."""
    quest = await db.get(DailyQuest, quest_id)
    if not quest or not quest.proof_image_url:
        raise NotFoundException("Quest proof image not found")
    if quest.user_id != current_user.id and not (current_user.is_mentor() or current_user.is_admin()):
        raise ForbiddenException("You cannot access this quest proof")
    prefix = "/uploads/"
    if not quest.proof_image_url.startswith(prefix):
        raise NotFoundException("Quest proof image not found")

    relative_key = quest.proof_image_url[len(prefix):]
    try:
        stored = await asyncio.to_thread(object_storage.read_upload, relative_key)
    except (FileNotFoundError, ValueError) as exc:
        raise NotFoundException("Quest proof image not found") from exc

    filename = PurePosixPath(relative_key).name
    return StreamingResponse(
        io.BytesIO(stored.content),
        media_type=stored.content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/daily/{quest_id:uuid}/complete", response_model=DailyQuestCompleteResponse)
async def complete_daily_quest(
    quest_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete one active Daily Quest and grant XP."""
    return await daily_quest_service.complete_quest(db, quest_id, current_user)
