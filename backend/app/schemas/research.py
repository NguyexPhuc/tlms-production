"""Contracts for research study setup and participant operations."""
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


StudyStatus = Literal["DRAFT", "PILOT", "ACTIVE", "CLOSED"]
ExperimentGroup = Literal["FIXED", "ADAPTIVE"]
ConsentStatus = Literal["NOT_REQUESTED", "PENDING", "GRANTED", "DECLINED", "WITHDRAWN"]
DataOrigin = Literal["REAL", "DEMO", "TEST", "SEED"]


class ResearchStudyCreate(BaseModel):
    study_code: str = Field(..., min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    study_status: StudyStatus = "DRAFT"


class ResearchStudyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    study_status: Optional[StudyStatus] = None
    pre_exam_id: Optional[UUID] = None
    post_exam_id: Optional[UUID] = None
    git_commit: Optional[str] = Field(None, min_length=7, max_length=64)
    question_bank_version: Optional[str] = Field(None, min_length=1, max_length=80)

    @model_validator(mode="after")
    def distinct_assessments(self):
        if self.pre_exam_id and self.pre_exam_id == self.post_exam_id:
            raise ValueError("PRE and POST assessments must be different exams")
        return self


class ResearchStudyResponse(BaseModel):
    id: UUID
    study_code: str
    name: Optional[str]
    description: Optional[str]
    study_status: str
    fixed_sequence_version: Optional[str]
    pre_exam_id: Optional[UUID]
    post_exam_id: Optional[UUID]
    git_commit: Optional[str]
    adaptive_algorithm_version: str
    adaptive_selection_policy_version: str
    fixed_selection_policy_version: str
    question_bank_version: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FixedSequenceConfigure(BaseModel):
    sequence_version: str = Field(..., min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    question_ids: list[UUID] = Field(..., min_length=1)

    @model_validator(mode="after")
    def unique_questions(self):
        if len(self.question_ids) != len(set(self.question_ids)):
            raise ValueError("Question IDs in a fixed sequence must be unique")
        return self


class FixedSequenceItemResponse(BaseModel):
    id: UUID
    study_code: str
    sequence_version: str
    position: int
    question_id: UUID
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchEnrollmentRequest(BaseModel):
    user_id: UUID
    study_code: str = Field(..., min_length=3, max_length=80)
    experiment_group: ExperimentGroup
    consent_status: ConsentStatus
    data_origin: DataOrigin

    @model_validator(mode="after")
    def consent_must_start_before_grant(self):
        if self.consent_status not in {"NOT_REQUESTED", "PENDING"}:
            raise ValueError(
                "New research enrollment must start with NOT_REQUESTED or PENDING consent"
            )
        return self


class ResearchConsentUpdate(BaseModel):
    consent_status: ConsentStatus


class ResearchParticipationResponse(BaseModel):
    id: UUID
    user_id: UUID
    participant_code: str
    study_code: Optional[str]
    experiment_group: str
    consent_status: str
    consent_granted_at: Optional[datetime]
    data_origin: str
    enrolled_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    active_for_research: bool = False

    model_config = {"from_attributes": True}


class ResearchParticipantProgressResponse(BaseModel):
    study_code: str
    study_name: Optional[str]
    participant_code: str
    experiment_group: str
    consent_status: str
    data_origin: str
    pre_exam_id: Optional[UUID]
    post_exam_id: Optional[UUID]
    pre_completed: bool
    train_completed: int
    train_required: int = 20
    post_completed: bool
    survey_completed: bool
    completed_at: Optional[datetime]


class ResearchSurveySubmit(BaseModel):
    likert_answers: list[int] = Field(..., min_length=10, max_length=10)
    useful_feedback: Optional[str] = Field(None, max_length=2000)
    improvement_feedback: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def validate_likert_range(self):
        if any(answer < 1 or answer > 5 for answer in self.likert_answers):
            raise ValueError("Every Likert answer must be between 1 and 5")
        return self


class ResearchSurveyResponse(BaseModel):
    id: UUID
    study_code: str
    likert_answers: list[int]
    useful_feedback: Optional[str]
    improvement_feedback: Optional[str]
    submitted_at: datetime

    model_config = {"from_attributes": True}

