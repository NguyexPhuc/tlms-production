"""Exam and digital certificate APIs."""
import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image
import io

from app.api.deps import get_current_user, require_admin, require_mentor
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.models.certification import Certificate, CertificateAuditLog, CertificateTemplate, CertificateVerificationLog
from app.models.user import User
from app.schemas.certification import (
    AdminExamResultResponse,
    AttemptResponse,
    AttemptSubmit,
    CertificateResponse,
    CertificateAuditLogResponse,
    CertificateRevokeRequest,
    CertificateStatistics,
    CertificateTemplateCreate,
    CertificateTemplateResponse,
    CertificateVerifyResponse,
    CertificateVerificationLogResponse,
    CourseCreate,
    CourseResponse,
    CourseUpdate,
    CourseEnrollmentResponse,
    ExamCreate,
    ExamResponse,
    ExamResultResponse,
    LessonCreate,
    LessonResponse,
    ManualAnswerReview,
    PendingExamAnswerResponse,
)
from app.services.certification import certification_service
from app.services.object_storage import object_storage


router = APIRouter(tags=["Digital Certification"])
settings = get_settings()


@router.get("/courses", response_model=list[CourseResponse])
async def list_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await certification_service.list_courses(db)


@router.get("/courses/enrollments/my", response_model=list[CourseEnrollmentResponse])
async def list_my_course_enrollments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await certification_service.list_my_enrollments(db, current_user)


@router.post("/courses/{course_id}/enroll", response_model=CourseEnrollmentResponse)
async def enroll_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await certification_service.enroll_course(db, current_user, course_id)


@router.get("/courses/{course_id}/lessons", response_model=list[LessonResponse])
async def list_course_lessons(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await certification_service.list_lessons(db, course_id)


@router.post("/admin/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await certification_service.create_course(db, admin, payload)


@router.get("/admin/courses", response_model=list[CourseResponse])
async def list_admin_courses(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await certification_service.list_courses(db, include_drafts=True)


@router.patch("/admin/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await certification_service.update_course(db, course_id, payload)


@router.post("/admin/courses/{course_id}/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_course_lesson(
    course_id: UUID,
    payload: LessonCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await certification_service.create_lesson(db, course_id, payload)


@router.get("/admin/courses/{course_id}/lessons", response_model=list[LessonResponse])
async def list_admin_course_lessons(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await certification_service.list_lessons(db, course_id, include_drafts=True)


@router.get("/exams", response_model=list[ExamResponse])
async def list_exams(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await certification_service.list_exams(db, current_user)


@router.get("/admin/exams", response_model=list[ExamResponse])
async def list_admin_exams(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await certification_service.list_exams(db, admin, include_drafts=True)


@router.post("/admin/exams", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def create_exam(
    payload: ExamCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    exam = await certification_service.create_exam(db, admin, payload)
    return certification_service.exam_summary(exam)


@router.post("/exams/{exam_id}/start", response_model=AttemptResponse)
async def start_exam(
    exam_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await certification_service.start_exam(db, current_user, exam_id)


@router.post("/exam-attempts/{attempt_id}/submit", response_model=ExamResultResponse)
async def submit_exam(
    attempt_id: UUID,
    payload: AttemptSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await certification_service.submit_exam(db, current_user, attempt_id, payload.answers)


@router.get("/exam-attempts/{attempt_id}/result", response_model=ExamResultResponse)
async def get_exam_result(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Ownership is checked before exposing the result.
    from app.models.certification import ExamAttempt

    attempt = await db.get(ExamAttempt, attempt_id)
    if not attempt:
        raise NotFoundException("Exam attempt not found")
    if attempt.user_id != current_user.id and not (current_user.is_admin() or current_user.is_mentor()):
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("You cannot access this exam result")
    return await certification_service.result_payload(db, attempt_id)


@router.post("/admin/exam-answers/{answer_id}/review")
async def review_manual_answer(
    answer_id: UUID,
    payload: ManualAnswerReview,
    db: AsyncSession = Depends(get_db),
    reviewer: User = Depends(require_mentor),
):
    return await certification_service.review_answer(db, reviewer, answer_id, payload.score_awarded, payload.feedback)


@router.get("/admin/exam-results", response_model=list[AdminExamResultResponse])
async def list_admin_exam_results(
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await certification_service.list_admin_results(db, min(max(limit, 1), 500))


@router.get("/admin/exam-answers/pending", response_model=list[PendingExamAnswerResponse])
async def list_pending_exam_answers(
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    reviewer: User = Depends(require_mentor),
):
    return await certification_service.list_pending_answers(db, min(max(limit, 1), 500))


@router.get("/certificates/verify/{token}", response_model=CertificateVerifyResponse)
async def verify_certificate(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    return await certification_service.verify_certificate(db, token, ip, request.headers.get("user-agent", ""))


@router.get("/certificates/my", response_model=list[CertificateResponse])
async def list_my_certificates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await certification_service.list_my_certificates(db, current_user)


@router.get("/certificates/{certificate_id}", response_model=CertificateResponse)
async def get_certificate(
    certificate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await certification_service.get_certificate(db, certificate_id, current_user)


@router.get("/certificates/{certificate_id}/download")
async def download_certificate(
    certificate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    certificate = await certification_service.get_certificate(db, certificate_id, current_user)
    if certificate.status == "revoked":
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Certificate has been revoked")
    if not certificate.pdf_storage_key:
        raise NotFoundException("Certificate PDF not found")
    try:
        stored = await asyncio.to_thread(object_storage.read_private, certificate.pdf_storage_key)
    except FileNotFoundError as exc:
        raise NotFoundException("Certificate PDF not found") from exc
    return StreamingResponse(
        io.BytesIO(stored.content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{certificate.certificate_id}.pdf"'},
    )


@router.get("/admin/certificates", response_model=list[CertificateResponse])
async def list_admin_certificates(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await certification_service.list_all_certificates(db)


@router.post("/admin/certificates/{certificate_id}/revoke", response_model=CertificateResponse)
async def revoke_certificate(
    certificate_id: UUID,
    payload: CertificateRevokeRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await certification_service.revoke(db, admin, certificate_id, payload.reason)


@router.get("/admin/certificate-statistics", response_model=CertificateStatistics)
async def certificate_statistics(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await certification_service.statistics(db)


@router.get("/admin/certificate-templates", response_model=list[CertificateTemplateResponse])
async def list_certificate_templates(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    await certification_service.ensure_default_template(db)
    await db.commit()
    return list((await db.execute(
        select(CertificateTemplate).order_by(CertificateTemplate.created_at.desc())
    )).scalars().all())


@router.post(
    "/admin/certificate-templates",
    response_model=CertificateTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_certificate_template(
    payload: CertificateTemplateCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if payload.is_default:
        existing = list((await db.execute(
            select(CertificateTemplate).where(CertificateTemplate.is_default.is_(True))
        )).scalars().all())
        for template in existing:
            template.is_default = False
    template = CertificateTemplate(**payload.model_dump(), created_by_id=admin.id)
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.post(
    "/admin/certificate-templates/{template_id}/assets/{kind}",
    response_model=CertificateTemplateResponse,
)
async def upload_certificate_template_asset(
    template_id: UUID,
    kind: str,
    asset: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if kind not in {"logo", "background"}:
        raise HTTPException(status_code=400, detail="Asset kind must be logo or background")
    content = await asset.read(5 * 1024 * 1024 + 1)
    if not content or len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must not exceed 5 MB")
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
            image_format = (image.format or "").upper()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid image file") from exc
    extensions = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}
    if image_format not in extensions:
        raise HTTPException(status_code=400, detail="Only PNG, JPEG and WebP are supported")
    template = await db.get(CertificateTemplate, template_id)
    if not template:
        raise NotFoundException("Certificate template not found")
    storage_key = await asyncio.to_thread(
        object_storage.put_private,
        f"template-assets/{template.id}-{kind}.{extensions[image_format]}",
        content,
        asset.content_type or "application/octet-stream",
    )
    if kind == "logo":
        template.logo_storage_key = storage_key
    else:
        template.background_storage_key = storage_key
    await db.commit()
    await db.refresh(template)
    return template


@router.get("/admin/certificate-audit-logs", response_model=list[CertificateAuditLogResponse])
async def list_certificate_audit_logs(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    safe_limit = min(max(limit, 1), 500)
    return list((await db.execute(
        select(CertificateAuditLog).order_by(CertificateAuditLog.created_at.desc()).limit(safe_limit)
    )).scalars().all())


@router.get("/admin/certificate-verification-logs", response_model=list[CertificateVerificationLogResponse])
async def list_certificate_verification_logs(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    safe_limit = min(max(limit, 1), 500)
    return list((await db.execute(
        select(CertificateVerificationLog)
        .order_by(CertificateVerificationLog.verified_at.desc())
        .limit(safe_limit)
    )).scalars().all())
