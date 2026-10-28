"""Weekly cup competition service."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pytz
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import BadRequestException, ForbiddenException
from app.models.cup import CupDefinition, UserCup, WeeklyCupAttempt, WeeklyCupEvent, WeeklyCupEventStatus
from app.models.user import User, UserRole, UserStatus


VN_TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")


CUP_DEFINITIONS: List[Dict[str, Any]] = [
    {"code": "cup_khoi_dong", "title": "Khởi động", "description": "Cup mở màn cho người dẫn đầu bài test tuần.", "icon": "C1", "color": "#f59e0b", "sort_order": 10},
    {"code": "cup_toc_do", "title": "Tốc độ", "description": "Dành cho người làm bài vừa chính xác vừa nhanh.", "icon": "C2", "color": "#ef4444", "sort_order": 20},
    {"code": "cup_ben_bi", "title": "Bền bỉ", "description": "Ghi nhận phong độ ổn định qua mỗi tuần.", "icon": "C3", "color": "#10b981", "sort_order": 30},
    {"code": "cup_ky_luat", "title": "Kỷ luật", "description": "Trao cho người đạt điểm cao và giữ chuyên cần tốt.", "icon": "C4", "color": "#22c55e", "sort_order": 40},
    {"code": "cup_sang_tao", "title": "Sáng tạo", "description": "Tôn vinh tư duy công nghệ linh hoạt.", "icon": "C5", "color": "#8b5cf6", "sort_order": 50},
    {"code": "cup_dong_doi", "title": "Đồng đội", "description": "Cup cho tinh thần học tập và hỗ trợ lab.", "icon": "C6", "color": "#06b6d4", "sort_order": 60},
    {"code": "cup_but_pha", "title": "Bứt phá", "description": "Dành cho người vượt mốc mạnh ở chặng cuối.", "icon": "C7", "color": "#f97316", "sort_order": 70},
    {"code": "cup_vo_dich", "title": "Vô địch", "description": "Cup cuối cùng cho người có kết quả nổi bật nhất.", "icon": "C8", "color": "#eab308", "sort_order": 80},
]


IT_QUIZ_QUESTIONS: List[Dict[str, Any]] = [
    {"id": "q01", "question": "Trong SQL, câu lệnh nào dùng để lấy dữ liệu từ bảng?", "options": [{"id": "A", "text": "SELECT"}, {"id": "B", "text": "INSERT"}, {"id": "C", "text": "UPDATE"}, {"id": "D", "text": "DELETE"}], "answer": "A"},
    {"id": "q02", "question": "Khóa chính trong database thường dùng để làm gì?", "options": [{"id": "A", "text": "Mã hóa dữ liệu"}, {"id": "B", "text": "Định danh duy nhất một dòng"}, {"id": "C", "text": "Sao lưu bảng"}, {"id": "D", "text": "Tạo giao diện"}], "answer": "B"},
    {"id": "q03", "question": "HTTP status code 404 có nghĩa là gì?", "options": [{"id": "A", "text": "Thành công"}, {"id": "B", "text": "Không có quyền"}, {"id": "C", "text": "Không tìm thấy tài nguyên"}, {"id": "D", "text": "Lỗi server"}], "answer": "C"},
    {"id": "q04", "question": "Trong REST API, phương thức nào thường dùng để tạo mới tài nguyên?", "options": [{"id": "A", "text": "GET"}, {"id": "B", "text": "POST"}, {"id": "C", "text": "TRACE"}, {"id": "D", "text": "HEAD"}], "answer": "B"},
    {"id": "q05", "question": "React hook nào dùng để quản lý state trong component?", "options": [{"id": "A", "text": "useState"}, {"id": "B", "text": "usePath"}, {"id": "C", "text": "useTable"}, {"id": "D", "text": "useSQL"}], "answer": "A"},
    {"id": "q06", "question": "JWT thường gồm mấy phần chính được ngăn cách bởi dấu chấm?", "options": [{"id": "A", "text": "1"}, {"id": "B", "text": "2"}, {"id": "C", "text": "3"}, {"id": "D", "text": "4"}], "answer": "C"},
    {"id": "q07", "question": "Docker image là gì?", "options": [{"id": "A", "text": "File ảnh giao diện"}, {"id": "B", "text": "Bản mẫu read-only để tạo container"}, {"id": "C", "text": "Một database"}, {"id": "D", "text": "Một package manager"}], "answer": "B"},
    {"id": "q08", "question": "Git command nào dùng để tạo commit?", "options": [{"id": "A", "text": "git push"}, {"id": "B", "text": "git branch"}, {"id": "C", "text": "git commit"}, {"id": "D", "text": "git pull"}], "answer": "C"},
    {"id": "q09", "question": "Index trong database giúp ích chủ yếu cho việc gì?", "options": [{"id": "A", "text": "Tăng tốc truy vấn đọc"}, {"id": "B", "text": "Xóa toàn bộ dữ liệu"}, {"id": "C", "text": "Đổi màu UI"}, {"id": "D", "text": "Tạo token"}], "answer": "A"},
    {"id": "q10", "question": "CSS Flexbox thường dùng để làm gì?", "options": [{"id": "A", "text": "Quản lý request backend"}, {"id": "B", "text": "Bố cục phần tử trên giao diện"}, {"id": "C", "text": "Chạy migration"}, {"id": "D", "text": "Tạo khóa chính"}], "answer": "B"},
    {"id": "q11", "question": "Trong Python, async/await thường dùng cho trường hợp nào?", "options": [{"id": "A", "text": "Xử lý bất đồng bộ"}, {"id": "B", "text": "Tạo CSS"}, {"id": "C", "text": "Nén ảnh"}, {"id": "D", "text": "Khai báo biến toàn cục"}], "answer": "A"},
    {"id": "q12", "question": "CORS liên quan đến vấn đề nào?", "options": [{"id": "A", "text": "Quyền truy cập tài nguyên giữa các origin"}, {"id": "B", "text": "Tốc độ ổ cứng"}, {"id": "C", "text": "Kiểu font"}, {"id": "D", "text": "Mật khẩu database"}], "answer": "A"},
    {"id": "q13", "question": "Trong SQL, JOIN dùng để làm gì?", "options": [{"id": "A", "text": "Kết hợp dữ liệu từ nhiều bảng"}, {"id": "B", "text": "Tắt server"}, {"id": "C", "text": "Tạo branch"}, {"id": "D", "text": "Format code"}], "answer": "A"},
    {"id": "q14", "question": "Backend framework FastAPI chạy trên ngôn ngữ nào?", "options": [{"id": "A", "text": "Python"}, {"id": "B", "text": "PHP"}, {"id": "C", "text": "Ruby"}, {"id": "D", "text": "Go only"}], "answer": "A"},
    {"id": "q15", "question": "Next.js App Router dùng thư mục chính nào để định nghĩa route?", "options": [{"id": "A", "text": "pages"}, {"id": "B", "text": "app"}, {"id": "C", "text": "routes.xml"}, {"id": "D", "text": "controllers"}], "answer": "B"},
    {"id": "q16", "question": "Biến môi trường thường dùng để lưu gì?", "options": [{"id": "A", "text": "Thông tin cấu hình như API URL, key"}, {"id": "B", "text": "Màu text duy nhất"}, {"id": "C", "text": "Tên file ảnh"}, {"id": "D", "text": "Nội dung commit"}], "answer": "A"},
    {"id": "q17", "question": "Transaction trong database giúp đảm bảo điều gì?", "options": [{"id": "A", "text": "Nhóm thao tác thành công hoặc rollback cùng nhau"}, {"id": "B", "text": "Tạo CSS animation"}, {"id": "C", "text": "Tự động dịch UI"}, {"id": "D", "text": "Tăng kích thước ảnh"}], "answer": "A"},
    {"id": "q18", "question": "Unit test dùng để kiểm tra gì?", "options": [{"id": "A", "text": "Một đơn vị logic nhỏ của code"}, {"id": "B", "text": "Tốc độ mạng Wi-Fi"}, {"id": "C", "text": "Màu logo"}, {"id": "D", "text": "Dung lượng RAM"}], "answer": "A"},
    {"id": "q19", "question": "HTTP status code 500 thường biểu thị điều gì?", "options": [{"id": "A", "text": "Request thành công"}, {"id": "B", "text": "Lỗi phía server"}, {"id": "C", "text": "Redirect vĩnh viễn"}, {"id": "D", "text": "Không có nội dung"}], "answer": "B"},
    {"id": "q20", "question": "Mục đích chính của migration database là gì?", "options": [{"id": "A", "text": "Theo dõi và áp dụng thay đổi schema"}, {"id": "B", "text": "Chạy frontend"}, {"id": "C", "text": "Tạo ảnh Docker"}, {"id": "D", "text": "Viết CSS"}], "answer": "A"},
]


class WeeklyCupService:
    """Create Friday-only cup events and award cups by quiz result."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def min_discipline_score(self) -> float:
        return float(self.settings.WEEKLY_CUP_MIN_DISCIPLINE)

    @property
    def open_weekday(self) -> int:
        return max(0, min(int(self.settings.WEEKLY_CUP_OPEN_WEEKDAY), 6))

    @property
    def open_hour(self) -> int:
        return max(0, min(int(self.settings.WEEKLY_CUP_OPEN_HOUR), 23))

    @property
    def duration_hours(self) -> int:
        return max(1, int(self.settings.WEEKLY_CUP_DURATION_HOURS))

    def _now_utc(self) -> datetime:
        return datetime.utcnow()

    def _now_vn(self) -> datetime:
        return datetime.now(VN_TIMEZONE)

    def _to_utc_naive(self, value: datetime) -> datetime:
        return value.astimezone(pytz.utc).replace(tzinfo=None)

    def _event_window(self, event_date: date) -> Tuple[datetime, datetime]:
        opens_vn = VN_TIMEZONE.localize(datetime.combine(event_date, time(hour=self.open_hour)))
        closes_vn = opens_vn + timedelta(hours=self.duration_hours)
        return self._to_utc_naive(opens_vn), self._to_utc_naive(closes_vn)

    def _target_event_date(self, now_vn: Optional[datetime] = None) -> date:
        now_vn = now_vn or self._now_vn()
        start_of_week = now_vn.date() - timedelta(days=now_vn.weekday())
        event_date = start_of_week + timedelta(days=self.open_weekday)
        opens_at, closes_at = self._event_window(event_date)
        now_utc = self._now_utc()
        if now_utc >= closes_at:
            event_date = event_date + timedelta(days=7)
        return event_date

    def _next_event_at(self) -> datetime:
        event_date = self._target_event_date()
        opens_at, _ = self._event_window(event_date)
        return opens_at

    async def ensure_catalog(self, db: AsyncSession) -> List[CupDefinition]:
        result = await db.execute(select(CupDefinition))
        existing_by_code = {cup.code: cup for cup in result.scalars().all()}

        for item in CUP_DEFINITIONS:
            cup = existing_by_code.get(item["code"])
            if cup is None:
                cup = CupDefinition(**item)
                db.add(cup)
                existing_by_code[item["code"]] = cup
                continue

            for key, value in item.items():
                setattr(cup, key, value)
            cup.is_active = True
            cup.updated_at = self._now_utc()

        await db.flush()
        return sorted(existing_by_code.values(), key=lambda cup: cup.sort_order)

    async def _get_available_cup(self, db: AsyncSession) -> Optional[CupDefinition]:
        assigned_cup_ids = select(WeeklyCupEvent.cup_id)
        result = await db.execute(
            select(CupDefinition)
            .where(CupDefinition.is_active.is_(True), CupDefinition.id.not_in(assigned_cup_ids))
            .order_by(CupDefinition.sort_order.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _learning_user_filters(self) -> Tuple[Any, ...]:
        return (
            User.status == UserStatus.ACTIVE,
            or_(User.roles.contains([UserRole.CANDIDATE.value]), User.roles.contains([UserRole.MEMBER.value])),
            ~User.roles.contains([UserRole.ADMIN.value]),
            ~User.roles.contains([UserRole.MENTOR.value]),
        )

    def _is_eligible_user(self, user: User) -> Tuple[bool, Optional[str]]:
        has_learning_role = user.has_role(UserRole.CANDIDATE.value) or user.has_role(UserRole.MEMBER.value)
        is_management_role = user.has_role(UserRole.ADMIN.value) or user.has_role(UserRole.MENTOR.value)
        if not has_learning_role:
            return False, "Chỉ thực tập sinh/thành viên được tham gia tranh cup."
        if is_management_role:
            return False, "Tài khoản admin/mentor không được tranh cup."
        if float(user.discipline_score or 0) < self.min_discipline_score:
            return False, f"Cần chuyên cần/kỷ luật từ {self.min_discipline_score:.0f}% trở lên."
        return True, None

    def _public_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [{"id": item["id"], "question": item["question"], "options": item["options"]} for item in questions]

    def _score_answers(self, questions: List[Dict[str, Any]], answers: Dict[str, str]) -> int:
        score = 0
        for question in questions:
            question_id = question["id"]
            if answers.get(question_id) == question["answer"]:
                score += 1
        return score

    def _user_summary(self, user: Optional[User]) -> Optional[Dict[str, Any]]:
        if user is None:
            return None
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "current_xp": user.current_xp,
            "level": user.calculate_level(),
            "discipline_score": round(float(user.discipline_score or 0), 1),
        }

    def _serialize_cup(self, cup: CupDefinition, award: Optional[UserCup] = None) -> Dict[str, Any]:
        return {
            "id": cup.id,
            "code": cup.code,
            "title": cup.title,
            "description": cup.description,
            "icon": cup.icon,
            "color": cup.color,
            "sort_order": cup.sort_order,
            "is_active": cup.is_active,
            "is_awarded": award is not None,
            "awarded_at": award.awarded_at if award else None,
            "awarded_to": self._user_summary(award.user) if award else None,
        }

    def _serialize_attempt(self, attempt: Optional[WeeklyCupAttempt]) -> Optional[Dict[str, Any]]:
        if attempt is None:
            return None
        return {
            "id": attempt.id,
            "event_id": attempt.event_id,
            "started_at": attempt.started_at,
            "submitted_at": attempt.submitted_at,
            "score": attempt.score,
            "total_questions": attempt.total_questions,
            "duration_seconds": attempt.duration_seconds,
            "answers": attempt.answers or {},
        }

    def _serialize_event(
        self,
        event: WeeklyCupEvent,
        award: Optional[UserCup] = None,
        include_questions: bool = False,
    ) -> Dict[str, Any]:
        return {
            "id": event.id,
            "week_start": event.week_start,
            "opens_at": event.opens_at,
            "closes_at": event.closes_at,
            "status": event.status,
            "cup": self._serialize_cup(event.cup, award),
            "winner": self._user_summary(event.winner),
            "winner_score": event.winner_score,
            "awarded_at": event.awarded_at,
            "questions": self._public_questions(event.questions or []) if include_questions else [],
        }

    async def _award_event_to_attempt(self, db: AsyncSession, event: WeeklyCupEvent, attempt: WeeklyCupAttempt) -> UserCup:
        existing_award = (
            await db.execute(select(UserCup).where(UserCup.cup_id == event.cup_id).options(selectinload(UserCup.user)))
        ).scalar_one_or_none()
        if existing_award is not None:
            event.status = WeeklyCupEventStatus.AWARDED.value
            event.winner_user_id = existing_award.user_id
            event.winner = existing_award.user
            event.winner_score = existing_award.score_snapshot
            event.awarded_at = existing_award.awarded_at
            return existing_award

        now = self._now_utc()
        award = UserCup(
            user_id=attempt.user_id,
            cup_id=event.cup_id,
            event_id=event.id,
            rank=1,
            score_snapshot=float(attempt.score or 0),
            discipline_score_snapshot=float(attempt.user.discipline_score or 0),
            awarded_at=now,
        )
        event.status = WeeklyCupEventStatus.AWARDED.value
        event.winner_user_id = attempt.user_id
        event.winner = attempt.user
        event.winner_score = float(attempt.score or 0)
        event.awarded_at = now

        db.add(award)
        await db.flush()
        award.user = attempt.user
        award.cup = event.cup
        award.event = event
        return award

    async def _ranked_attempts(self, db: AsyncSession, event_id: Any, limit: Optional[int] = None) -> List[WeeklyCupAttempt]:
        query = (
            select(WeeklyCupAttempt)
            .where(WeeklyCupAttempt.event_id == event_id, WeeklyCupAttempt.submitted_at.isnot(None))
            .options(selectinload(WeeklyCupAttempt.user))
            .order_by(
                WeeklyCupAttempt.score.desc(),
                WeeklyCupAttempt.duration_seconds.asc(),
                WeeklyCupAttempt.submitted_at.asc(),
            )
        )
        if limit is not None:
            query = query.limit(limit)
        return list((await db.execute(query)).scalars().all())

    async def finalize_expired_events(self, db: AsyncSession) -> int:
        now = self._now_utc()
        result = await db.execute(
            select(WeeklyCupEvent)
            .where(
                WeeklyCupEvent.closes_at <= now,
                WeeklyCupEvent.status.in_([WeeklyCupEventStatus.SCHEDULED.value, WeeklyCupEventStatus.OPEN.value]),
            )
            .options(selectinload(WeeklyCupEvent.cup), selectinload(WeeklyCupEvent.winner))
        )
        events = result.scalars().all()
        finalized = 0

        for event in events:
            top_attempts = await self._ranked_attempts(db, event.id, limit=1)
            if not top_attempts:
                event.status = WeeklyCupEventStatus.CLOSED.value
                finalized += 1
                continue
            await self._award_event_to_attempt(db, event, top_attempts[0])
            finalized += 1

        await db.flush()
        return finalized

    async def ensure_current_event(self, db: AsyncSession) -> Optional[WeeklyCupEvent]:
        await self.ensure_catalog(db)
        await self.finalize_expired_events(db)

        event_date = self._target_event_date()
        result = await db.execute(
            select(WeeklyCupEvent)
            .where(WeeklyCupEvent.week_start == event_date)
            .options(selectinload(WeeklyCupEvent.cup), selectinload(WeeklyCupEvent.winner))
        )
        event = result.scalar_one_or_none()
        now = self._now_utc()

        if event is not None:
            if not event.questions:
                event.questions = IT_QUIZ_QUESTIONS
            if event.opens_at <= now < event.closes_at and event.status == WeeklyCupEventStatus.SCHEDULED.value:
                event.status = WeeklyCupEventStatus.OPEN.value
            elif now < event.opens_at and event.status == WeeklyCupEventStatus.OPEN.value:
                event.status = WeeklyCupEventStatus.SCHEDULED.value
            return event

        cup = await self._get_available_cup(db)
        if cup is None:
            return None

        opens_at, closes_at = self._event_window(event_date)
        status = WeeklyCupEventStatus.OPEN.value if opens_at <= now < closes_at else WeeklyCupEventStatus.SCHEDULED.value
        event = WeeklyCupEvent(
            cup_id=cup.id,
            cup=cup,
            week_start=event_date,
            opens_at=opens_at,
            closes_at=closes_at,
            status=status,
            questions=IT_QUIZ_QUESTIONS,
        )
        db.add(event)
        await db.flush()
        return event

    async def _awards_by_cup_id(self, db: AsyncSession) -> Dict[Any, UserCup]:
        result = await db.execute(
            select(UserCup).options(selectinload(UserCup.user), selectinload(UserCup.cup), selectinload(UserCup.event))
        )
        return {award.cup_id: award for award in result.scalars().all()}

    async def _award_for_event(self, db: AsyncSession, event: Optional[WeeklyCupEvent]) -> Optional[UserCup]:
        if event is None:
            return None
        return (
            await db.execute(
                select(UserCup)
                .where(UserCup.event_id == event.id)
                .options(selectinload(UserCup.user), selectinload(UserCup.cup), selectinload(UserCup.event))
            )
        ).scalar_one_or_none()

    async def _attempt_for_user(self, db: AsyncSession, event: Optional[WeeklyCupEvent], user: User) -> Optional[WeeklyCupAttempt]:
        if event is None:
            return None
        return (
            await db.execute(
                select(WeeklyCupAttempt)
                .where(WeeklyCupAttempt.event_id == event.id, WeeklyCupAttempt.user_id == user.id)
                .options(selectinload(WeeklyCupAttempt.user))
            )
        ).scalar_one_or_none()

    async def get_dashboard(self, db: AsyncSession, user: User) -> Dict[str, Any]:
        cups = await self.ensure_catalog(db)
        event = await self.ensure_current_event(db)
        award_map = await self._awards_by_cup_id(db)
        event_award = await self._award_for_event(db, event)
        my_attempt = await self._attempt_for_user(db, event, user)

        ranked_attempts = await self._ranked_attempts(db, event.id, limit=10) if event else []
        leaderboard = []
        my_rank = None
        for index, attempt in enumerate(ranked_attempts, start=1):
            if attempt.user_id == user.id:
                my_rank = index
            leaderboard.append(
                {
                    "rank": index,
                    "user_id": attempt.user_id,
                    "email": attempt.user.email,
                    "full_name": attempt.user.full_name,
                    "level": attempt.user.calculate_level(),
                    "current_xp": attempt.user.current_xp,
                    "discipline_score": round(float(attempt.user.discipline_score or 0), 1),
                    "score": attempt.score,
                    "total_questions": attempt.total_questions,
                    "duration_seconds": attempt.duration_seconds,
                    "submitted_at": attempt.submitted_at,
                    "eligible": True,
                }
            )

        eligible, reason = self._is_eligible_user(user)
        event_is_open = bool(event and event.status == WeeklyCupEventStatus.OPEN.value)
        can_start = bool(event_is_open and eligible and event_award is None and (my_attempt is None or my_attempt.submitted_at is None))
        can_submit = bool(event_is_open and eligible and my_attempt is not None and my_attempt.submitted_at is None)
        include_questions = can_submit

        awarded_count = (await db.execute(select(func.count(UserCup.id)))).scalar() or 0
        active_cup_count = len([cup for cup in cups if cup.is_active])

        return {
            "event": self._serialize_event(event, event_award, include_questions=include_questions) if event else None,
            "cups": [self._serialize_cup(cup, award_map.get(cup.id)) for cup in cups if cup.is_active],
            "leaderboard": leaderboard,
            "my_eligibility": {
                "eligible": eligible,
                "reason": reason,
                "discipline_score": round(float(user.discipline_score or 0), 1),
                "min_discipline_score": self.min_discipline_score,
                "my_rank": my_rank,
                "can_start": can_start,
                "can_submit": can_submit,
            },
            "my_attempt": self._serialize_attempt(my_attempt),
            "remaining_cups": max(0, active_cup_count - int(awarded_count)),
            "min_discipline_score": self.min_discipline_score,
            "next_event_at": self._next_event_at(),
            "updated_at": self._now_utc(),
        }

    async def start_current_quiz(self, db: AsyncSession, user: User) -> Dict[str, Any]:
        event = await self.ensure_current_event(db)
        if event is None:
            raise BadRequestException("Không còn cup nào để mở sự kiện tranh cup.")
        if event.status != WeeklyCupEventStatus.OPEN.value:
            raise BadRequestException("Bài kiểm tra chỉ mở trong ngày thứ 6.")

        eligible, reason = self._is_eligible_user(user)
        if not eligible:
            raise ForbiddenException(reason or "Bạn chưa đủ điều kiện tham gia.")

        attempt = await self._attempt_for_user(db, event, user)
        if attempt is None:
            attempt = WeeklyCupAttempt(
                event_id=event.id,
                user_id=user.id,
                answers={},
                total_questions=len(event.questions or IT_QUIZ_QUESTIONS),
                started_at=self._now_utc(),
            )
            db.add(attempt)
            await db.flush()
        elif attempt.submitted_at is not None:
            raise BadRequestException("Bạn đã nộp bài kiểm tra cup tuần này.")

        return {
            "message": "Bài kiểm tra đã bắt đầu.",
            "dashboard": await self.get_dashboard(db, user),
        }

    async def submit_current_quiz(self, db: AsyncSession, user: User, answers: Dict[str, str]) -> Dict[str, Any]:
        event = await self.ensure_current_event(db)
        if event is None or event.status != WeeklyCupEventStatus.OPEN.value:
            raise BadRequestException("Bài kiểm tra cup hiện không mở.")

        eligible, reason = self._is_eligible_user(user)
        if not eligible:
            raise ForbiddenException(reason or "Bạn chưa đủ điều kiện tham gia.")

        attempt = await self._attempt_for_user(db, event, user)
        if attempt is None:
            raise BadRequestException("Bạn cần bắt đầu bài kiểm tra trước khi nộp.")
        if attempt.submitted_at is not None:
            raise BadRequestException("Bạn đã nộp bài kiểm tra cup tuần này.")

        now = self._now_utc()
        questions = event.questions or IT_QUIZ_QUESTIONS
        score = self._score_answers(questions, answers)
        duration_seconds = max(0, int((now - attempt.started_at).total_seconds()))

        attempt.answers = answers
        attempt.score = score
        attempt.total_questions = len(questions)
        attempt.duration_seconds = duration_seconds
        attempt.submitted_at = now
        attempt.updated_at = now
        await db.flush()

        return {
            "message": "Đã nộp bài kiểm tra cup.",
            "score": score,
            "total_questions": len(questions),
            "duration_seconds": duration_seconds,
            "dashboard": await self.get_dashboard(db, user),
        }


weekly_cup_service = WeeklyCupService()
