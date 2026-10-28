"""Validation and response contracts for exams and certificates."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CourseCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    is_published: bool = False
    certificate_template_id: Optional[UUID] = None


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    skills: Optional[List[str]] = None
    is_published: Optional[bool] = None
    certificate_template_id: Optional[UUID] = None


class CourseResponse(BaseModel):
    id: UUID
    code: str
    title: str
    description: Optional[str]
    skills: List[str]
    is_published: bool
    certificate_template_id: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class LessonCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    content: Optional[str] = None
    position: int = Field(..., ge=1)
    is_published: bool = False


class LessonResponse(BaseModel):
    id: UUID
    course_id: UUID
    title: str
    content: Optional[str]
    position: int
    is_published: bool

    model_config = {"from_attributes": True}


class CourseEnrollmentResponse(BaseModel):
    id: UUID
    course_id: UUID
    user_id: UUID
    status: str
    progress_percentage: float
    enrolled_at: datetime

    model_config = {"from_attributes": True}


class ExamQuestionCreate(BaseModel):
    question_id: UUID
    position: int = Field(..., ge=1)
    points: float = Field(1.0, gt=0, le=1000)
    correct_options: Optional[List[str]] = None


class ExamCreate(BaseModel):
    course_id: UUID
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    duration_minutes: int = Field(30, ge=1, le=480)
    pass_percentage: float = Field(80.0, ge=0, le=100)
    max_attempts: int = Field(1, ge=1, le=20)
    is_published: bool = False
    certificate_name: Optional[str] = Field(None, max_length=255)
    certificate_valid_days: Optional[int] = Field(None, ge=1, le=3650)
    opens_at: Optional[datetime] = None
    closes_at: Optional[datetime] = None
    questions: List[ExamQuestionCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_window(self):
        if self.opens_at and self.closes_at and self.closes_at <= self.opens_at:
            raise ValueError("closes_at must be after opens_at")
        positions = [item.position for item in self.questions]
        if len(set(positions)) != len(positions):
            raise ValueError("Question positions must be unique")
        return self


class ExamQuestionPublic(BaseModel):
    id: UUID
    question_id: UUID
    position: int
    points: float
    title: str
    question: str
    description: Optional[str]
    question_type: str
    options: Optional[Dict[str, str]]
    allow_multiple: bool = False


class ExamResponse(BaseModel):
    id: UUID
    course_id: UUID
    course_title: str
    title: str
    description: Optional[str]
    duration_minutes: int
    pass_percentage: float
    max_attempts: int
    is_published: bool
    certificate_name: Optional[str]
    opens_at: Optional[datetime]
    closes_at: Optional[datetime]
    question_count: int
    attempts_used: int = 0
    best_percentage: Optional[float] = None


class AttemptAnswerSubmit(BaseModel):
    exam_question_id: UUID
    selected_options: Optional[List[str]] = None
    text_answer: Optional[str] = Field(None, max_length=10000)

    @model_validator(mode="after")
    def require_answer(self):
        if not self.selected_options and not (self.text_answer or "").strip():
            raise ValueError("An answer is required")
        return self


class AttemptSubmit(BaseModel):
    answers: List[AttemptAnswerSubmit] = Field(..., min_length=1)


class AttemptResponse(BaseModel):
    id: UUID
    exam_id: UUID
    exam_title: str
    attempt_number: int
    status: str
    started_at: datetime
    expires_at: datetime
    submitted_at: Optional[datetime]
    questions: List[ExamQuestionPublic]


class ExamResultResponse(BaseModel):
    id: Optional[UUID]
    attempt_id: UUID
    score: float
    max_score: float
    percentage: float
    passed: bool
    proficiency_level: str
    status: str
    certificate_id: Optional[UUID] = None
    verification_token: Optional[str] = None


class AdminExamResultResponse(BaseModel):
    id: UUID
    attempt_id: UUID
    user_id: UUID
    user_name: str
    user_email: str
    exam_id: UUID
    exam_title: str
    course_title: str
    score: float
    max_score: float
    percentage: float
    passed: bool
    proficiency_level: str
    graded_at: datetime
    certificate_id: Optional[UUID] = None


class PendingExamAnswerResponse(BaseModel):
    id: UUID
    attempt_id: UUID
    user_id: UUID
    user_name: str
    user_email: str
    exam_title: str
    question_title: str
    question_text: str
    text_answer: Optional[str]
    max_points: float
    submitted_at: datetime


class CertificateTemplateCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    organization_name: str = Field("T&A Lab", min_length=2, max_length=255)
    title: str = Field("CERTIFICATE OF ACHIEVEMENT", min_length=2, max_length=255)
    subtitle: str = Field("DIGITAL TECHNOLOGY & PROFESSIONAL SKILLS", max_length=255)
    primary_color: str = Field("#C8102E", pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str = Field("#101D35", pattern=r"^#[0-9A-Fa-f]{6}$")
    accent_color: str = Field("#C6A15B", pattern=r"^#[0-9A-Fa-f]{6}$")
    background_color: str = Field("#FFFCF5", pattern=r"^#[0-9A-Fa-f]{6}$")
    signature_name: Optional[str] = Field(None, max_length=160)
    signature_title: Optional[str] = Field(None, max_length=160)
    font_family: str = Field("DejaVu Sans", max_length=100)
    layout: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class CertificateTemplateResponse(CertificateTemplateCreate):
    id: UUID
    logo_storage_key: Optional[str] = None
    background_storage_key: Optional[str] = None
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CertificateResponse(BaseModel):
    id: UUID
    certificate_id: str
    full_name: str
    certificate_name: str
    issuer_name: str
    score: float
    proficiency_level: str
    skills: List[str]
    issued_at: datetime
    expires_at: Optional[datetime]
    status: str
    verification_token: str
    score_is_public: bool

    model_config = {"from_attributes": True}


class CertificateVerifyResponse(BaseModel):
    verification_status: str
    certificate_id: Optional[str] = None
    full_name: Optional[str] = None
    certificate_name: Optional[str] = None
    issuer_name: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    score: Optional[float] = None
    proficiency_level: Optional[str] = None
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class CertificateRevokeRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=2000)


class CertificateStatistics(BaseModel):
    total_users: int
    total_attempts: int
    pass_rate: float
    total_certificates: int
    valid_certificates: int
    expired_certificates: int
    revoked_certificates: int


class ManualAnswerReview(BaseModel):
    score_awarded: float = Field(..., ge=0)
    feedback: Optional[str] = Field(None, max_length=5000)


class CertificateAuditLogResponse(BaseModel):
    id: UUID
    certificate_id: UUID
    actor_id: Optional[UUID]
    action: str
    reason: Optional[str]
    metadata_json: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class CertificateVerificationLogResponse(BaseModel):
    id: UUID
    certificate_id: Optional[UUID]
    token_fingerprint: str
    result: str
    user_agent: Optional[str]
    verified_at: datetime

    model_config = {"from_attributes": True}
