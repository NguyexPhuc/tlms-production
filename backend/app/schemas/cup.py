"""Schemas for weekly cup competitions."""
from datetime import date, datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CupUserSummary(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    current_xp: int
    level: int
    discipline_score: float


class CupDefinitionResponse(BaseModel):
    id: UUID
    code: str
    title: str
    description: str
    icon: str
    color: str
    sort_order: int
    is_active: bool
    is_awarded: bool = False
    awarded_at: Optional[datetime] = None
    awarded_to: Optional[CupUserSummary] = None

    class Config:
        from_attributes = True


class WeeklyCupQuestionOption(BaseModel):
    id: str
    text: str


class WeeklyCupQuestion(BaseModel):
    id: str
    question: str
    options: List[WeeklyCupQuestionOption]


class WeeklyCupAttemptResponse(BaseModel):
    id: UUID
    event_id: UUID
    started_at: datetime
    submitted_at: Optional[datetime] = None
    score: Optional[int] = None
    total_questions: int
    duration_seconds: Optional[int] = None
    answers: Dict[str, str] = Field(default_factory=dict)


class WeeklyCupEventResponse(BaseModel):
    id: UUID
    week_start: date
    opens_at: datetime
    closes_at: datetime
    status: str
    cup: CupDefinitionResponse
    winner: Optional[CupUserSummary] = None
    winner_score: Optional[float] = None
    awarded_at: Optional[datetime] = None
    questions: List[WeeklyCupQuestion] = Field(default_factory=list)


class WeeklyCupLeaderboardEntry(BaseModel):
    rank: int
    user_id: UUID
    email: str
    full_name: Optional[str] = None
    level: int
    current_xp: int
    discipline_score: float
    score: Optional[int] = None
    total_questions: int = 20
    duration_seconds: Optional[int] = None
    submitted_at: Optional[datetime] = None
    eligible: bool


class WeeklyCupEligibility(BaseModel):
    eligible: bool
    reason: Optional[str] = None
    discipline_score: float
    min_discipline_score: float
    my_rank: Optional[int] = None
    can_start: bool = False
    can_submit: bool = False


class WeeklyCupDashboardResponse(BaseModel):
    event: Optional[WeeklyCupEventResponse] = None
    cups: List[CupDefinitionResponse]
    leaderboard: List[WeeklyCupLeaderboardEntry]
    my_eligibility: WeeklyCupEligibility
    my_attempt: Optional[WeeklyCupAttemptResponse] = None
    remaining_cups: int
    min_discipline_score: float
    next_event_at: Optional[datetime] = None
    updated_at: datetime


class WeeklyCupStartResponse(BaseModel):
    message: str
    dashboard: WeeklyCupDashboardResponse


class WeeklyCupSubmitRequest(BaseModel):
    answers: Dict[str, str]


class WeeklyCupSubmitResponse(BaseModel):
    message: str
    score: int
    total_questions: int
    duration_seconds: int
    dashboard: WeeklyCupDashboardResponse
