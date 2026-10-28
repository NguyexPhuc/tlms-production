"""Transactional exam grading, certificate issuance, PDF and verification."""
from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import secrets
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Deque, Dict, Iterable, Optional
from uuid import UUID

import qrcode
from fastapi import HTTPException
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.certification import (
    Certificate, CertificateAuditLog, CertificateTemplate,
    CertificateVerificationLog, Course, CourseEnrollment, Exam, ExamAnswer, ExamAttempt,
    ExamQuestion, ExamResult, Lesson,
)
from app.models.development import Question
from app.models.user import User
from app.schemas.certification import CourseCreate, CourseUpdate, ExamCreate, LessonCreate
from app.services.notification import notification_service
from app.services.object_storage import object_storage


logger = logging.getLogger(__name__)
settings = get_settings()
OBJECTIVE_TYPES = {"multiple_choice", "single_choice", "true_false", "mcq", "objective"}


class VerificationRateLimiter:
    """Per-process limiter; use a shared Redis limiter when scaling horizontally."""

    def __init__(self) -> None:
        self._requests: Dict[str, Deque[datetime]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = datetime.utcnow()
        bucket = self._requests[key]
        while bucket and (now - bucket[0]).total_seconds() >= 60:
            bucket.popleft()
        if len(bucket) >= settings.CERTIFICATE_VERIFY_RATE_LIMIT:
            return False
        bucket.append(now)
        return True


verification_rate_limiter = VerificationRateLimiter()


class CertificationService:
    async def ensure_default_template(self, db: AsyncSession) -> CertificateTemplate:
        template = (await db.execute(
            select(CertificateTemplate)
            .where(CertificateTemplate.is_default.is_(True), CertificateTemplate.is_active.is_(True))
            .order_by(CertificateTemplate.created_at.asc())
        )).scalars().first()
        if template:
            return template
        template = CertificateTemplate(
            name="Premium Technology Certificate",
            organization_name=settings.CERTIFICATE_ISSUER_NAME,
            is_default=True,
            layout={"page": "A4_portrait", "design": "premium_technology_v1"},
        )
        db.add(template)
        await db.flush()
        return template

    async def create_course(self, db: AsyncSession, actor: User, payload: CourseCreate) -> Course:
        exists = (await db.execute(
            select(Course.id).where(func.lower(Course.code) == payload.code.lower())
        )).scalar_one_or_none()
        if exists:
            raise BadRequestException("Course code already exists")
        course = Course(**payload.model_dump(), created_by_id=actor.id)
        db.add(course)
        await db.commit()
        await db.refresh(course)
        return course

    async def list_courses(self, db: AsyncSession, include_drafts: bool = False) -> list[Course]:
        query = select(Course)
        if not include_drafts:
            query = query.where(Course.is_published.is_(True))
        return list((await db.execute(query.order_by(Course.created_at.desc()))).scalars().all())

    async def update_course(self, db: AsyncSession, course_id: UUID, payload: CourseUpdate) -> Course:
        course = await db.get(Course, course_id)
        if not course:
            raise NotFoundException("Course not found")
        values = payload.model_dump(exclude_unset=True)
        template_id = values.get("certificate_template_id")
        if template_id and not await db.get(CertificateTemplate, template_id):
            raise NotFoundException("Certificate template not found")
        for field, value in values.items():
            setattr(course, field, value)
        await db.commit()
        await db.refresh(course)
        return course

    async def enroll_course(self, db: AsyncSession, user: User, course_id: UUID) -> CourseEnrollment:
        course = await db.get(Course, course_id)
        if not course or not course.is_published:
            raise NotFoundException("Course not found")
        enrollment = (await db.execute(select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.user_id == user.id,
        ))).scalar_one_or_none()
        if enrollment:
            return enrollment
        enrollment = CourseEnrollment(course_id=course_id, user_id=user.id)
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)
        return enrollment

    async def list_my_enrollments(self, db: AsyncSession, user: User) -> list[CourseEnrollment]:
        return list((await db.execute(select(CourseEnrollment).where(
            CourseEnrollment.user_id == user.id
        ).order_by(CourseEnrollment.enrolled_at.desc()))).scalars().all())

    async def create_lesson(self, db: AsyncSession, course_id: UUID, payload: LessonCreate) -> Lesson:
        if not await db.get(Course, course_id):
            raise NotFoundException("Course not found")
        duplicate = (await db.execute(select(Lesson.id).where(
            Lesson.course_id == course_id, Lesson.position == payload.position
        ))).scalar_one_or_none()
        if duplicate:
            raise BadRequestException("Lesson position already exists in this course")
        lesson = Lesson(course_id=course_id, **payload.model_dump())
        db.add(lesson)
        await db.commit()
        await db.refresh(lesson)
        return lesson

    async def list_lessons(self, db: AsyncSession, course_id: UUID, include_drafts: bool = False) -> list[Lesson]:
        query = select(Lesson).where(Lesson.course_id == course_id)
        if not include_drafts:
            query = query.where(Lesson.is_published.is_(True))
        return list((await db.execute(query.order_by(Lesson.position.asc()))).scalars().all())

    async def create_exam(self, db: AsyncSession, actor: User, payload: ExamCreate) -> Exam:
        course = await db.get(Course, payload.course_id)
        if not course:
            raise NotFoundException("Course not found")
        question_ids = [item.question_id for item in payload.questions]
        questions = list((await db.execute(
            select(Question).where(Question.id.in_(question_ids))
        )).scalars().all())
        by_id = {question.id: question for question in questions}
        if len(by_id) != len(set(question_ids)):
            raise BadRequestException("One or more questions do not exist")

        exam = Exam(**payload.model_dump(exclude={"questions"}), created_by_id=actor.id)
        db.add(exam)
        await db.flush()
        for item in payload.questions:
            question = by_id[item.question_id]
            correct = item.correct_options or question.correct_options or ([question.correct_option] if question.correct_option else [])
            if question.question_type in OBJECTIVE_TYPES and not correct:
                raise BadRequestException(f"Question '{question.title}' has no server-side correct answer")
            db.add(ExamQuestion(
                exam_id=exam.id,
                question_id=item.question_id,
                position=item.position,
                points=item.points,
                correct_options=sorted({value.upper() for value in correct}),
            ))
        await db.commit()
        return await self.get_exam_entity(db, exam.id)

    async def get_exam_entity(self, db: AsyncSession, exam_id: UUID) -> Exam:
        exam = (await db.execute(
            select(Exam).where(Exam.id == exam_id).options(
                selectinload(Exam.course),
                selectinload(Exam.exam_questions).selectinload(ExamQuestion.question),
            )
        )).scalar_one_or_none()
        if not exam:
            raise NotFoundException("Exam not found")
        return exam

    async def list_exams(self, db: AsyncSession, user: User, include_drafts: bool = False) -> list[dict]:
        query = select(Exam).options(selectinload(Exam.course), selectinload(Exam.exam_questions))
        if not include_drafts:
            query = query.join(Course).where(Exam.is_published.is_(True), Course.is_published.is_(True))
        exams = list((await db.execute(query.order_by(Exam.created_at.desc()))).scalars().unique().all())
        rows = []
        for exam in exams:
            attempts_used = (await db.execute(
                select(func.count(ExamAttempt.id)).where(
                    ExamAttempt.exam_id == exam.id,
                    ExamAttempt.user_id == user.id,
                )
            )).scalar() or 0
            results = list((await db.execute(
                select(ExamResult.percentage).where(ExamResult.exam_id == exam.id, ExamResult.user_id == user.id)
            )).scalars().all())
            rows.append(self.exam_summary(exam, attempts_used, max(results) if results else None))
        return rows

    @staticmethod
    def exam_summary(exam: Exam, attempts_used: int = 0, best_percentage: Optional[float] = None) -> dict:
        return {
            "id": exam.id, "course_id": exam.course_id, "course_title": exam.course.title,
            "title": exam.title, "description": exam.description,
            "duration_minutes": exam.duration_minutes, "pass_percentage": exam.pass_percentage,
            "max_attempts": exam.max_attempts, "is_published": exam.is_published,
            "certificate_name": exam.certificate_name, "opens_at": exam.opens_at,
            "closes_at": exam.closes_at, "question_count": len(exam.exam_questions),
            "attempts_used": attempts_used, "best_percentage": best_percentage,
        }

    async def start_exam(self, db: AsyncSession, user: User, exam_id: UUID) -> dict:
        exam = await self.get_exam_entity(db, exam_id)
        now = datetime.utcnow()
        if not exam.is_published or not exam.course.is_published:
            raise NotFoundException("Exam not found")
        enrollment = (await db.execute(select(CourseEnrollment.id).where(
            CourseEnrollment.course_id == exam.course_id,
            CourseEnrollment.user_id == user.id,
            CourseEnrollment.status == "active",
        ))).scalar_one_or_none()
        if not enrollment:
            raise ForbiddenException("Enroll in the course before starting its exam")
        if exam.opens_at and now < exam.opens_at:
            raise BadRequestException("Exam is not open yet")
        if exam.closes_at and now >= exam.closes_at:
            raise BadRequestException("Exam has closed")
        if not exam.exam_questions:
            raise BadRequestException("Exam has no questions")
        active = (await db.execute(select(ExamAttempt).where(
            ExamAttempt.exam_id == exam.id, ExamAttempt.user_id == user.id,
            ExamAttempt.status == "in_progress",
        ))).scalar_one_or_none()
        if active and active.expires_at > now:
            return self.attempt_payload(active, exam)
        if active:
            active.status = "expired"
        count = (await db.execute(select(func.count(ExamAttempt.id)).where(
            ExamAttempt.exam_id == exam.id, ExamAttempt.user_id == user.id,
        ))).scalar() or 0
        if count >= exam.max_attempts:
            raise BadRequestException("Maximum exam attempts reached")
        expires_at = now + timedelta(minutes=exam.duration_minutes)
        if exam.closes_at:
            expires_at = min(expires_at, exam.closes_at)
        attempt = ExamAttempt(
            exam_id=exam.id, user_id=user.id, attempt_number=count + 1,
            started_at=now, expires_at=expires_at,
        )
        db.add(attempt)
        await db.commit()
        await db.refresh(attempt)
        return self.attempt_payload(attempt, exam)

    @staticmethod
    def attempt_payload(attempt: ExamAttempt, exam: Exam) -> dict:
        questions = [{
            "id": item.id, "question_id": item.question.id, "position": item.position,
            "points": item.points, "title": item.question.title,
            "question": item.question.question, "description": item.question.description,
            "question_type": item.question.question_type, "options": item.question.options,
            "allow_multiple": len(item.correct_options or []) > 1,
        } for item in exam.exam_questions]
        return {
            "id": attempt.id, "exam_id": exam.id, "exam_title": exam.title,
            "attempt_number": attempt.attempt_number, "status": attempt.status,
            "started_at": attempt.started_at, "expires_at": attempt.expires_at,
            "submitted_at": attempt.submitted_at, "questions": questions,
        }

    async def submit_exam(self, db: AsyncSession, user: User, attempt_id: UUID, answers: Iterable) -> dict:
        attempt = (await db.execute(
            select(ExamAttempt).where(ExamAttempt.id == attempt_id, ExamAttempt.user_id == user.id).with_for_update()
        )).scalar_one_or_none()
        if not attempt:
            raise NotFoundException("Exam attempt not found")
        if attempt.status in {"passed", "failed"}:
            return await self.result_payload(db, attempt.id)
        if attempt.status != "in_progress":
            raise BadRequestException("Exam attempt cannot be submitted")
        now = datetime.utcnow()
        if now > attempt.expires_at:
            attempt.status = "expired"
            await db.commit()
            raise HTTPException(status_code=409, detail="Exam time has expired")

        exam = await self.get_exam_entity(db, attempt.exam_id)
        items = {item.id: item for item in exam.exam_questions}
        submitted = list(answers)
        submitted_ids = [answer.exam_question_id for answer in submitted]
        if len(submitted_ids) != len(set(submitted_ids)) or set(submitted_ids) != set(items):
            raise BadRequestException("All exam questions must be answered exactly once")
        manual_review = False
        for payload in submitted:
            item = items[payload.exam_question_id]
            selected = sorted({value.upper() for value in (payload.selected_options or [])})
            if item.question.question_type in OBJECTIVE_TYPES:
                allowed = {value.upper() for value in (item.question.options or {}).keys()}
                if not selected or not set(selected).issubset(allowed):
                    raise BadRequestException("Invalid answer option")
                correct = selected == sorted({value.upper() for value in (item.correct_options or [])})
                awarded = item.points if correct else 0.0
            else:
                manual_review, correct, awarded = True, None, None
            db.add(ExamAnswer(
                attempt_id=attempt.id, exam_question_id=item.id,
                selected_options=selected or None,
                text_answer=(payload.text_answer or "").strip() or None,
                is_correct=correct, score_awarded=awarded,
            ))
        attempt.submitted_at = now
        attempt.status = "pending_review" if manual_review else "submitted"
        await db.flush()
        if manual_review:
            await db.commit()
            return self.pending_result_payload(attempt, exam)
        result = await self._finalize_result(db, attempt, exam)
        await db.commit()
        return await self._result_to_payload(db, result)

    @staticmethod
    def pending_result_payload(attempt: ExamAttempt, exam: Exam) -> dict:
        return {
            "id": None, "attempt_id": attempt.id, "score": 0,
            "max_score": sum(item.points for item in exam.exam_questions), "percentage": 0,
            "passed": False, "proficiency_level": "pending_review", "status": "pending_review",
            "certificate_id": None, "verification_token": None,
        }

    async def review_answer(self, db: AsyncSession, reviewer: User, answer_id: UUID, score: float, feedback: Optional[str]) -> dict:
        answer = (await db.execute(
            select(ExamAnswer).where(ExamAnswer.id == answer_id).options(
                selectinload(ExamAnswer.exam_question), selectinload(ExamAnswer.attempt)
            ).with_for_update()
        )).scalar_one_or_none()
        if not answer:
            raise NotFoundException("Exam answer not found")
        if score > answer.exam_question.points:
            raise BadRequestException("Awarded score exceeds question points")
        answer.score_awarded = score
        answer.is_correct = score >= answer.exam_question.points
        answer.reviewer_feedback = feedback
        answer.reviewed_by_id = reviewer.id
        answer.reviewed_at = datetime.utcnow()
        await db.flush()
        remaining = (await db.execute(select(func.count(ExamAnswer.id)).where(
            ExamAnswer.attempt_id == answer.attempt_id, ExamAnswer.score_awarded.is_(None)
        ))).scalar() or 0
        if remaining:
            await db.commit()
            return {"status": "pending_review", "remaining": remaining}
        exam = await self.get_exam_entity(db, answer.attempt.exam_id)
        result = await self._finalize_result(db, answer.attempt, exam)
        await db.commit()
        return await self._result_to_payload(db, result)

    async def _finalize_result(self, db: AsyncSession, attempt: ExamAttempt, exam: Exam) -> ExamResult:
        existing = (await db.execute(select(ExamResult).where(ExamResult.attempt_id == attempt.id))).scalar_one_or_none()
        if existing:
            return existing
        awarded = float((await db.execute(select(func.coalesce(func.sum(ExamAnswer.score_awarded), 0)).where(
            ExamAnswer.attempt_id == attempt.id
        ))).scalar() or 0)
        maximum = float(sum(item.points for item in exam.exam_questions))
        percentage = round((awarded / maximum * 100) if maximum else 0, 2)
        result = ExamResult(
            attempt_id=attempt.id, user_id=attempt.user_id, exam_id=exam.id,
            score=awarded, max_score=maximum, percentage=percentage,
            passed=percentage >= exam.pass_percentage,
            proficiency_level=self.proficiency_level(percentage),
        )
        db.add(result)
        attempt.status = "passed" if result.passed else "failed"
        await db.flush()
        if result.passed:
            user = await db.get(User, attempt.user_id)
            await self.issue_certificate(db, user, exam, result)
        return result

    @staticmethod
    def proficiency_level(percentage: float) -> str:
        if percentage >= 95:
            return "Expert"
        if percentage >= 85:
            return "Advanced"
        if percentage >= 70:
            return "Proficient"
        return "Developing"

    async def issue_certificate(self, db: AsyncSession, user: User, exam: Exam, result: ExamResult) -> Certificate:
        if not result.passed:
            raise ForbiddenException("A passing result is required")
        existing = (await db.execute(
            select(Certificate).where(Certificate.exam_result_id == result.id)
        )).scalar_one_or_none()
        if existing:
            return existing
        template = await db.get(CertificateTemplate, exam.course.certificate_template_id) if exam.course.certificate_template_id else None
        if not template or not template.is_active:
            template = await self.ensure_default_template(db)
        now = datetime.utcnow()
        certificate = Certificate(
            certificate_id=await self._new_certificate_id(db), user_id=user.id,
            course_id=exam.course_id, exam_result_id=result.id, template_id=template.id,
            full_name=user.full_name, certificate_name=exam.certificate_name or exam.course.title,
            issuer_name=template.organization_name, score=result.percentage,
            proficiency_level=result.proficiency_level, skills=exam.course.skills or [], issued_at=now,
            expires_at=now + timedelta(days=exam.certificate_valid_days) if exam.certificate_valid_days else None,
            verification_token=secrets.token_urlsafe(32), template_version=template.version,
        )
        db.add(certificate)
        await db.flush()
        certificate.pdf_storage_key = await asyncio.to_thread(self.render_pdf, certificate, template)
        db.add(CertificateAuditLog(
            certificate_id=certificate.id, action="issued",
            metadata_json={"exam_id": str(exam.id), "result_id": str(result.id)},
        ))
        await notification_service.create_notification(
            db, user.id, "certificate_issued", "Bạn đã nhận chứng chỉ",
            f"Chứng chỉ {certificate.certificate_name} đã được cấp.",
            payload={"certificate_id": str(certificate.id)},
        )
        return certificate

    async def _new_certificate_id(self, db: AsyncSession) -> str:
        for _ in range(10):
            value = f"TECH-{datetime.utcnow().year}-{secrets.token_hex(3).upper()}"
            if not (await db.execute(select(Certificate.id).where(Certificate.certificate_id == value))).scalar_one_or_none():
                return value
        raise RuntimeError("Could not allocate a unique certificate ID")

    def render_pdf(self, certificate: Certificate, template: CertificateTemplate) -> str:
        verify_url = f"{settings.PUBLIC_WEB_URL.rstrip('/')}/verify/{certificate.verification_token}"
        regular, bold = self._register_fonts(getattr(template, "font_family", "DejaVu Sans"))
        page_w, page_h = A4
        layout = getattr(template, "layout", None) or {}
        qr_x = page_w * min(max(float(layout.get("qr_x_pct", 76)), 5), 82) / 100
        qr_y = page_h * min(max(float(layout.get("qr_y_pct", 7.5)), 4), 22) / 100
        signature_x = page_w * min(max(float(layout.get("signature_x_pct", 24)), 18), 76) / 100
        signature_y = page_h * min(max(float(layout.get("signature_y_pct", 13.3)), 7), 24) / 100
        pdf_buffer = io.BytesIO()
        pdf = canvas.Canvas(pdf_buffer, pagesize=A4, pageCompression=1)
        pdf.setTitle(f"Certificate {certificate.certificate_id}")
        pdf.setAuthor(certificate.issuer_name)
        pdf.setFillColor(HexColor(template.background_color))
        pdf.rect(0, 0, page_w, page_h, fill=1, stroke=0)
        background_storage_key = getattr(template, "background_storage_key", None)
        if background_storage_key and object_storage.private_exists(background_storage_key):
            try:
                background = object_storage.read_private(background_storage_key)
                pdf.drawImage(ImageReader(io.BytesIO(background.content)), 0, 0, page_w, page_h, mask="auto")
            except Exception:
                logger.warning("Could not render certificate background %s", background_storage_key, exc_info=True)
        pdf.setStrokeColor(HexColor(template.primary_color)); pdf.setLineWidth(4)
        pdf.rect(24, 24, page_w - 48, page_h - 48, fill=0, stroke=1)
        pdf.setStrokeColor(HexColor(template.accent_color)); pdf.setLineWidth(1.2)
        pdf.rect(34, 34, page_w - 68, page_h - 68, fill=0, stroke=1)
        pdf.setStrokeColor(HexColor("#E4DCCB")); pdf.setLineWidth(0.35)
        for y in range(95, 760, 55):
            pdf.line(45, y, 100, y); pdf.circle(104, y, 2, fill=0, stroke=1)
            pdf.line(page_w - 100, y + 18, page_w - 45, y + 18)
            pdf.circle(page_w - 104, y + 18, 2, fill=0, stroke=1)
        pdf.setFillColor(HexColor(template.primary_color)); pdf.circle(page_w - 58, page_h - 58, 34, fill=1, stroke=0)
        pdf.setStrokeColor(HexColor(template.accent_color)); pdf.circle(page_w - 58, page_h - 58, 23, fill=0, stroke=1)
        brand_x = 58
        logo_storage_key = getattr(template, "logo_storage_key", None)
        if logo_storage_key and object_storage.private_exists(logo_storage_key):
            try:
                logo = object_storage.read_private(logo_storage_key)
                pdf.drawImage(ImageReader(io.BytesIO(logo.content)), 58, page_h - 110, 42, 42, preserveAspectRatio=True, mask="auto")
                brand_x = 112
            except Exception:
                logger.warning("Could not render certificate logo %s", logo_storage_key, exc_info=True)
        pdf.setFillColor(HexColor(template.secondary_color)); pdf.setFont(bold, 13)
        pdf.drawString(brand_x, page_h - 78, template.organization_name.upper())
        pdf.setFont(regular, 8); pdf.drawString(brand_x, page_h - 94, "DIGITAL LEARNING & PROFESSIONAL ASSESSMENT")
        pdf.setFillColor(HexColor(template.primary_color)); pdf.setFont(bold, 24)
        pdf.drawCentredString(page_w / 2, page_h - 185, template.title)
        pdf.setFillColor(HexColor(template.accent_color)); pdf.setFont(bold, 10)
        pdf.drawCentredString(page_w / 2, page_h - 209, template.subtitle)
        pdf.setFillColor(HexColor(template.secondary_color)); pdf.setFont(regular, 11)
        pdf.drawCentredString(page_w / 2, page_h - 270, "This is to certify that")
        pdf.setFont(bold, self._name_font_size(certificate.full_name))
        pdf.drawCentredString(page_w / 2, page_h - 315, certificate.full_name)
        pdf.setStrokeColor(HexColor(template.accent_color)); pdf.line(110, page_h - 328, page_w - 110, page_h - 328)
        pdf.setFont(regular, 10.5)
        pdf.drawCentredString(page_w / 2, page_h - 365, "has successfully completed the professional assessment")
        pdf.setFont(bold, 16)
        self._draw_centered_wrapped(pdf, certificate.certificate_name, page_w / 2, page_h - 402, 430, bold, 16)
        pdf.setFont(regular, 9.5)
        pdf.drawCentredString(page_w / 2, page_h - 447, "and demonstrated the required technical skills and professional competencies.")
        details = [
            ("Certificate ID", certificate.certificate_id), ("Final Score", f"{certificate.score:.2f}%"),
            ("Proficiency", certificate.proficiency_level), ("Issue Date", certificate.issued_at.strftime("%d/%m/%Y")),
            ("Expiration", certificate.expires_at.strftime("%d/%m/%Y") if certificate.expires_at else "No expiration"),
        ]
        for index, (label, value) in enumerate(details):
            x, y = 70 + (index % 2) * 245, page_h - 510 - (index // 2) * 48
            pdf.setFont(regular, 7.5); pdf.setFillColor(HexColor("#6B7280")); pdf.drawString(x, y, label.upper())
            pdf.setFont(bold, 10); pdf.setFillColor(HexColor(template.secondary_color)); pdf.drawString(x, y - 16, value)
        qr_buffer = io.BytesIO(); qrcode.make(verify_url).save(qr_buffer, format="PNG"); qr_buffer.seek(0)
        pdf.drawImage(ImageReader(qr_buffer), qr_x, qr_y, 78, 78, preserveAspectRatio=True, mask="auto")
        pdf.setFont(regular, 6.5); pdf.setFillColor(HexColor("#4B5563")); pdf.drawCentredString(qr_x + 39, qr_y - 11, "SCAN TO VERIFY")
        pdf.setStrokeColor(HexColor(template.secondary_color)); pdf.line(signature_x - 77, signature_y, signature_x + 78, signature_y)
        pdf.setFont(bold, 9); pdf.setFillColor(HexColor(template.secondary_color))
        pdf.drawCentredString(signature_x, signature_y - 16, template.signature_name or "Authorized Representative")
        pdf.setFont(regular, 7.5); pdf.drawCentredString(signature_x, signature_y - 30, template.signature_title or certificate.issuer_name)
        pdf.setFont(regular, 6.5); pdf.drawCentredString(page_w / 2, 48, verify_url)
        pdf.save()
        return object_storage.put_private(
            f"{certificate.id}.pdf",
            pdf_buffer.getvalue(),
            "application/pdf",
        )

    @staticmethod
    def _register_fonts(font_family: str = "DejaVu Sans") -> tuple[str, str]:
        sans_candidates = [
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ]
        serif_candidates = [
            ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
            ("C:/Windows/Fonts/times.ttf", "C:/Windows/Fonts/timesbd.ttf"),
        ]
        use_serif = "serif" in (font_family or "").lower()
        candidates = serif_candidates + sans_candidates if use_serif else sans_candidates
        regular_name = "CertificateSerif" if use_serif else "CertificateSans"
        bold_name = f"{regular_name}Bold"
        for regular, bold in candidates:
            if Path(regular).exists() and Path(bold).exists():
                try:
                    pdfmetrics.registerFont(TTFont(regular_name, regular))
                    pdfmetrics.registerFont(TTFont(bold_name, bold))
                except KeyError:
                    pass
                return regular_name, bold_name
        return ("Times-Roman", "Times-Bold") if use_serif else ("Helvetica", "Helvetica-Bold")

    @staticmethod
    def _name_font_size(name: str) -> int:
        return 17 if len(name) > 45 else 20 if len(name) > 32 else 24

    @staticmethod
    def _draw_centered_wrapped(pdf, text: str, center_x: float, y: float, max_width: float, font: str, size: int) -> None:
        lines, current = [], ""
        for word in text.split():
            candidate = f"{current} {word}".strip()
            if pdfmetrics.stringWidth(candidate, font, size) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        for index, line in enumerate(lines[:2]):
            pdf.drawCentredString(center_x, y - index * 21, line)

    async def result_payload(self, db: AsyncSession, attempt_id: UUID) -> dict:
        result = (await db.execute(select(ExamResult).where(ExamResult.attempt_id == attempt_id))).scalar_one_or_none()
        if not result:
            raise NotFoundException("Exam result not found")
        return await self._result_to_payload(db, result)

    async def _result_to_payload(self, db: AsyncSession, result: ExamResult) -> dict:
        certificate = (await db.execute(
            select(Certificate).where(Certificate.exam_result_id == result.id)
        )).scalar_one_or_none()
        return {
            "id": result.id, "attempt_id": result.attempt_id, "score": result.score,
            "max_score": result.max_score, "percentage": result.percentage,
            "passed": result.passed, "proficiency_level": result.proficiency_level,
            "status": "graded", "certificate_id": certificate.id if certificate else None,
            "verification_token": certificate.verification_token if certificate else None,
        }

    async def list_my_certificates(self, db: AsyncSession, user: User) -> list[Certificate]:
        await self.expire_certificates(db)
        return list((await db.execute(
            select(Certificate).where(Certificate.user_id == user.id).order_by(Certificate.issued_at.desc())
        )).scalars().all())

    async def list_all_certificates(self, db: AsyncSession) -> list[Certificate]:
        await self.expire_certificates(db)
        return list((await db.execute(
            select(Certificate).order_by(Certificate.issued_at.desc())
        )).scalars().all())

    async def expire_certificates(self, db: AsyncSession) -> int:
        rows = list((await db.execute(select(Certificate).where(
            Certificate.status == "valid",
            Certificate.expires_at.is_not(None),
            Certificate.expires_at <= datetime.utcnow(),
        ))).scalars().all())
        for certificate in rows:
            certificate.status = "expired"
            db.add(CertificateAuditLog(certificate_id=certificate.id, action="expired"))
        if rows:
            await db.commit()
        return len(rows)

    async def get_certificate(self, db: AsyncSession, certificate_id: UUID, user: User) -> Certificate:
        certificate = await db.get(Certificate, certificate_id)
        if not certificate:
            raise NotFoundException("Certificate not found")
        if certificate.user_id != user.id and not user.is_admin():
            raise ForbiddenException("You cannot access this certificate")
        return certificate

    async def verify_certificate(self, db: AsyncSession, token: str, ip: str, user_agent: str) -> dict:
        if not verification_rate_limiter.allow(ip or "unknown"):
            raise HTTPException(status_code=429, detail="Too many verification requests")
        certificate = (await db.execute(
            select(Certificate).where(Certificate.verification_token == token)
        )).scalar_one_or_none()
        now = datetime.utcnow()
        result = (
            "NOT_FOUND" if not certificate else "REVOKED" if certificate.status == "revoked"
            else "EXPIRED" if certificate.expires_at and certificate.expires_at <= now else "VALID"
        )
        db.add(CertificateVerificationLog(
            certificate_id=certificate.id if certificate else None,
            token_fingerprint=hashlib.sha256(token.encode()).hexdigest(), result=result,
            ip_hash=hashlib.sha256((ip or "unknown").encode()).hexdigest(),
            user_agent=(user_agent or "")[:500],
        ))
        await db.commit()
        if not certificate:
            return {"verification_status": result, "skills": []}
        return {
            "verification_status": result, "certificate_id": certificate.certificate_id,
            "full_name": certificate.full_name, "certificate_name": certificate.certificate_name,
            "issuer_name": certificate.issuer_name, "skills": certificate.skills or [],
            "score": certificate.score if certificate.score_is_public else None,
            "proficiency_level": certificate.proficiency_level,
            "issued_at": certificate.issued_at, "expires_at": certificate.expires_at,
        }

    async def revoke(self, db: AsyncSession, actor: User, certificate_id: UUID, reason: str) -> Certificate:
        certificate = (await db.execute(
            select(Certificate).where(Certificate.id == certificate_id).with_for_update()
        )).scalar_one_or_none()
        if not certificate:
            raise NotFoundException("Certificate not found")
        if certificate.status != "revoked":
            certificate.status, certificate.revoked_at, certificate.revoked_reason = "revoked", datetime.utcnow(), reason
            db.add(CertificateAuditLog(
                certificate_id=certificate.id, actor_id=actor.id, action="revoked", reason=reason,
            ))
            await db.commit()
            await db.refresh(certificate)
        return certificate

    async def statistics(self, db: AsyncSession) -> dict:
        now = datetime.utcnow()
        total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        total_attempts = (await db.execute(select(func.count(ExamAttempt.id)))).scalar() or 0
        total_results = (await db.execute(select(func.count(ExamResult.id)))).scalar() or 0
        passed = (await db.execute(select(func.count(ExamResult.id)).where(ExamResult.passed.is_(True)))).scalar() or 0
        total = (await db.execute(select(func.count(Certificate.id)))).scalar() or 0
        revoked = (await db.execute(select(func.count(Certificate.id)).where(Certificate.status == "revoked"))).scalar() or 0
        expired = (await db.execute(select(func.count(Certificate.id)).where(
            Certificate.status != "revoked", Certificate.expires_at.is_not(None), Certificate.expires_at <= now,
        ))).scalar() or 0
        return {
            "total_users": total_users, "total_attempts": total_attempts,
            "pass_rate": round((passed / total_results * 100) if total_results else 0, 2),
            "total_certificates": total, "valid_certificates": max(0, total - revoked - expired),
            "expired_certificates": expired, "revoked_certificates": revoked,
        }

    async def list_admin_results(self, db: AsyncSession, limit: int = 200) -> list[dict]:
        rows = (await db.execute(
            select(ExamResult, User, Exam, Course, Certificate)
            .join(User, User.id == ExamResult.user_id)
            .join(Exam, Exam.id == ExamResult.exam_id)
            .join(Course, Course.id == Exam.course_id)
            .outerjoin(Certificate, Certificate.exam_result_id == ExamResult.id)
            .order_by(ExamResult.graded_at.desc())
            .limit(limit)
        )).all()
        return [{
            "id": result.id,
            "attempt_id": result.attempt_id,
            "user_id": user.id,
            "user_name": user.full_name,
            "user_email": user.email,
            "exam_id": exam.id,
            "exam_title": exam.title,
            "course_title": course.title,
            "score": result.score,
            "max_score": result.max_score,
            "percentage": result.percentage,
            "passed": result.passed,
            "proficiency_level": result.proficiency_level,
            "graded_at": result.graded_at,
            "certificate_id": certificate.id if certificate else None,
        } for result, user, exam, course, certificate in rows]

    async def list_pending_answers(self, db: AsyncSession, limit: int = 200) -> list[dict]:
        rows = (await db.execute(
            select(ExamAnswer, ExamAttempt, User, Exam, ExamQuestion, Question)
            .join(ExamAttempt, ExamAttempt.id == ExamAnswer.attempt_id)
            .join(User, User.id == ExamAttempt.user_id)
            .join(Exam, Exam.id == ExamAttempt.exam_id)
            .join(ExamQuestion, ExamQuestion.id == ExamAnswer.exam_question_id)
            .join(Question, Question.id == ExamQuestion.question_id)
            .where(
                ExamAttempt.status == "pending_review",
                ExamAnswer.score_awarded.is_(None),
            )
            .order_by(ExamAttempt.submitted_at.asc())
            .limit(limit)
        )).all()
        return [{
            "id": answer.id,
            "attempt_id": attempt.id,
            "user_id": user.id,
            "user_name": user.full_name,
            "user_email": user.email,
            "exam_title": exam.title,
            "question_title": question.title,
            "question_text": question.question,
            "text_answer": answer.text_answer,
            "max_points": exam_question.points,
            "submitted_at": attempt.submitted_at or attempt.started_at,
        } for answer, attempt, user, exam, exam_question, question in rows]


certification_service = CertificationService()
