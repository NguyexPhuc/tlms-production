"""Question schemas for member development."""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.development import QuestionAnswerStatus, QuestionStatus
from app.models.task import TaskCreatorType, TaskDifficulty
from app.models.user import MemberLevel


class QuestionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    question: str = Field(..., min_length=1)
    description: Optional[str] = None
    difficulty: TaskDifficulty = TaskDifficulty.MEDIUM
    category: Optional[str] = Field(None, max_length=100)
    topic: Optional[str] = Field(None, max_length=120)
    skill_key: Optional[str] = Field(None, max_length=80)
    question_type: str = Field("short_answer", max_length=40)
    numeric_difficulty: float = Field(3.0, ge=1.0, le=10.0)
    source: str = Field("manager", max_length=40)
    learning_objective: Optional[str] = None
    is_baseline: bool = False
    points: int = Field(0, ge=0)
    expected_duration_minutes: Optional[int] = Field(None, ge=1)
    target_member_level: MemberLevel = MemberLevel.NEW
    creator_type: TaskCreatorType = TaskCreatorType.MANAGER
    expected_answer: Optional[str] = None
    accepted_concepts: Optional[List[List[str]]] = None
    options: Optional[Dict[str, str]] = None
    correct_option: Optional[str] = Field(None, pattern="^[A-Da-d]$")
    correct_options: Optional[List[str]] = None
    feedback: Optional[str] = None

    @model_validator(mode="after")
    def validate_objective_answer(self):
        objective_types = {"single_choice", "multiple_choice", "true_false", "mcq", "objective"}
        if self.question_type not in objective_types:
            return self
        if not self.options or len(self.options) < 2:
            raise ValueError("Objective questions require at least two options")
        allowed = {key.upper() for key in self.options}
        answers = self.correct_options or ([self.correct_option] if self.correct_option else [])
        answers = sorted({value.upper() for value in answers if value})
        if not answers or not set(answers).issubset(allowed):
            raise ValueError("Correct answers must reference existing options")
        if self.question_type == "multiple_choice" and len(answers) < 2:
            raise ValueError("Multiple-choice questions require at least two correct options")
        self.correct_options = answers
        self.correct_option = answers[0] if len(answers) == 1 else None
        return self


class QuestionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    question: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    difficulty: Optional[TaskDifficulty] = None
    category: Optional[str] = Field(None, max_length=100)
    topic: Optional[str] = Field(None, max_length=120)
    skill_key: Optional[str] = Field(None, max_length=80)
    question_type: Optional[str] = Field(None, max_length=40)
    numeric_difficulty: Optional[float] = Field(None, ge=1.0, le=10.0)
    source: Optional[str] = Field(None, max_length=40)
    learning_objective: Optional[str] = None
    is_baseline: Optional[bool] = None
    points: Optional[int] = Field(None, ge=0)
    expected_duration_minutes: Optional[int] = Field(None, ge=1)
    target_member_level: Optional[MemberLevel] = None
    creator_type: Optional[TaskCreatorType] = None
    expected_answer: Optional[str] = None
    accepted_concepts: Optional[List[List[str]]] = None
    options: Optional[Dict[str, str]] = None
    correct_option: Optional[str] = Field(None, pattern="^[A-Da-d]$")
    correct_options: Optional[List[str]] = None
    feedback: Optional[str] = None
    status: Optional[QuestionStatus] = None


class QuestionResponse(BaseModel):
    id: UUID
    title: str
    question: str
    description: Optional[str] = None
    difficulty: TaskDifficulty
    category: Optional[str] = None
    topic: Optional[str] = None
    skill_key: Optional[str] = None
    question_type: str = "short_answer"
    numeric_difficulty: float = 3.0
    source: str = "manager"
    learning_objective: Optional[str] = None
    is_baseline: bool = False
    points: int
    expected_duration_minutes: Optional[int] = None
    target_member_level: MemberLevel
    creator_type: TaskCreatorType
    created_by_id: Optional[UUID] = None
    options: Optional[Dict[str, str]] = None
    feedback: Optional[str] = None
    status: QuestionStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True


class QuestionListResponse(BaseModel):
    questions: List[QuestionResponse]
    total: int


class QuestionAnswerSubmit(BaseModel):
    answer: str = Field(..., min_length=1)


class QuestionAnswerReview(BaseModel):
    status: QuestionAnswerStatus
    manager_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    final_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    feedback: Optional[str] = None


class QuestionAnswerResponse(BaseModel):
    id: UUID
    user_id: UUID
    question_id: UUID
    question: Optional[QuestionResponse] = None
    answer: str
    ai_score: Optional[float] = None
    ai_feedback: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_breakdown: Optional[dict] = None
    manager_score: Optional[float] = None
    final_score: Optional[float] = None
    points_awarded: int = 0
    feedback: Optional[str] = None
    status: QuestionAnswerStatus
    reviewed_by_id: Optional[UUID] = None
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True
