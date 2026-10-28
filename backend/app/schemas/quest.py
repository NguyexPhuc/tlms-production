"""Schemas for Daily Quest APIs."""
from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.quest import DailyQuestDifficulty, DailyQuestStatus, DailyQuestType


class DailyQuestResponse(BaseModel):
    id: UUID
    user_id: UUID
    created_by_id: UUID | None = None
    title: str
    description: str
    quest_type: DailyQuestType = DailyQuestType.DAILY
    difficulty: DailyQuestDifficulty
    xp_reward: int
    status: DailyQuestStatus
    created_at: datetime
    expires_at: datetime
    completed_at: datetime | None = None
    proof_text: str | None = None
    proof_link: str | None = None
    proof_image_url: str | None = None
    proof_image_name: str | None = None
    submitted_at: datetime | None = None
    ai_score: float | None = None
    ai_feedback: str | None = None
    reviewed_at: datetime | None = None
    requires_image_proof: bool = False
    auto_pass_score: int = 70

    class Config:
        from_attributes = True
        use_enum_values = True


class DailyQuestListResponse(BaseModel):
    quests: List[DailyQuestResponse]
    total: int
    reset_at: datetime
    max_quests: int
    active_count: int
    completed_count: int
    expired_count: int


class DailyQuestLimitResponse(BaseModel):
    max_quests: int
    generated_count: int
    active_count: int
    completed_count: int
    expired_count: int
    remaining_generation_slots: int
    reset_at: datetime


class DailyQuestCompleteResponse(BaseModel):
    quest: DailyQuestResponse
    current_xp: int
    level: int


class DailyQuestProofSubmitResponse(DailyQuestCompleteResponse):
    passed: bool


class LimitQuestCreateRequest(BaseModel):
    target_user_ids: List[UUID] = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    difficulty: DailyQuestDifficulty = DailyQuestDifficulty.MEDIUM
    xp_reward: int = Field(default=50, ge=0, le=500)
    expires_at: datetime | None = None
    auto_pass_score: int = Field(default=70, ge=0, le=100)


class LimitQuestCreateResponse(BaseModel):
    quests: List[DailyQuestResponse]
    created_count: int
