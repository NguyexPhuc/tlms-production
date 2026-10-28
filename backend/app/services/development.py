"""Member development service."""
import json
import logging
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional
from uuid import UUID

import pytz
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.core.config import get_settings
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.development import (
    DailyTaskReport,
    DailyTaskStatus,
    MemberEvaluation,
    MemberRoadmap,
    MemberRoadmapWeek,
    Notification,
    PromotionReview,
    PromotionStatus,
    QuestionAnswerStatus,
    TaskProgressUpdate,
    UserQuestionAnswer,
)
from app.models.quest import DailyQuest, DailyQuestStatus
from app.models.task import Task, TaskCreatorType, TaskDifficulty, TaskStatus, UserTask
from app.models.user import MemberLevel, User, UserRole, UserStatus
from app.schemas.development import DailyTaskAssignRequest
from app.services.achievement import achievement_service
from app.services.ai_json import ai_json_service
from app.services.notification import notification_service

logger = logging.getLogger(__name__)

VN_TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")

NEXT_MEMBER_LEVEL: Dict[MemberLevel, MemberLevel] = {
    MemberLevel.NEW: MemberLevel.DILIGENT,
    MemberLevel.DILIGENT: MemberLevel.OFFICIAL,
}

ROADMAP_TOTAL_WEEKS = 8
ROADMAP_TOTAL_DAYS = 56

ROADMAP_WEEK_TEMPLATES: List[Dict[str, object]] = [
    {
        "week_number": 1,
        "title": "Week 1 - Onboarding",
        "stage": "LÀM QUEN & BASELINE",
        "goals": [
            "Làm quen quy trình Lab",
            "Xác định năng lực ban đầu",
            "Hoàn thành initial assessment",
        ],
        "question_focus": "Question cơ bản để thu thập baseline, chưa kết luận mạnh/yếu quá sớm.",
        "daily_task_focus": "Các task nhỏ về Git, Docker, quy trình làm việc và cách nộp minh chứng.",
        "quest_focus": "Quest làm quen hệ thống, ghi chú điều đã học và điểm còn chưa rõ.",
        "skill_targets": ["git", "workflow", "communication", "baseline"],
    },
    {
        "week_number": 2,
        "title": "Week 2 - Foundation",
        "stage": "NỀN TẢNG",
        "goals": [
            "Củng cố kiến thức nền",
            "Bắt đầu cá nhân hóa question",
            "Xác định điểm mạnh/yếu ban đầu",
        ],
        "question_focus": "Question nền tảng theo skill chính, bắt đầu gom evidence cho skill profile.",
        "daily_task_focus": "Task đọc code, thử API, ghi lại hiểu biết và lỗi gặp phải.",
        "quest_focus": "Quest củng cố kiến thức nền và tự giải thích lại bằng ví dụ ngắn.",
        "skill_targets": ["backend", "database", "frontend", "problem_solving"],
    },
    {
        "week_number": 3,
        "title": "Week 3 - Practice",
        "stage": "THỰC HÀNH & CẢI THIỆN",
        "goals": [
            "Tăng lượng question thực hành",
            "Kiểm tra khả năng áp dụng kiến thức",
            "Theo dõi consistency",
        ],
        "question_focus": "Question thực hành và tình huống áp dụng kiến thức vào code/project.",
        "daily_task_focus": "Task có kết quả kiểm tra được, ưu tiên minh chứng rõ ràng.",
        "quest_focus": "Quest thực hành từng bước nhỏ trên hệ thống thật.",
        "skill_targets": ["api", "debugging", "implementation", "testing"],
    },
    {
        "week_number": 4,
        "title": "Week 4 - First Review",
        "stage": "REVIEW THÁNG 1",
        "goals": [
            "Tổng hợp dữ liệu tháng đầu",
            "Đánh giá accuracy, difficulty và completion",
            "Xác định focus tháng tiếp theo",
        ],
        "question_focus": "Question review để kiểm tra lại các topic đã học trong tháng đầu.",
        "daily_task_focus": "Task tổng hợp learning notes, lỗi đã sửa và phần còn yếu.",
        "quest_focus": "Quest phản tư tháng 1 và chuẩn bị mục tiêu cá nhân hóa.",
        "skill_targets": ["review", "learning_speed", "weak_skills", "strong_skills"],
    },
    {
        "week_number": 5,
        "title": "Week 5 - Specialization",
        "stage": "CHUYÊN SÂU CÁ NHÂN",
        "goals": [
            "Tập trung skill mạnh và skill cần cải thiện",
            "Không lặp lại câu quá dễ",
            "Bắt đầu định hướng chuyên môn",
        ],
        "question_focus": "Question theo skill cá nhân, vừa phát huy điểm mạnh vừa vá knowledge gap.",
        "daily_task_focus": "Task có định hướng chuyên môn và yêu cầu tự giải thích quyết định kỹ thuật.",
        "quest_focus": "Quest luyện lại topic yếu theo khoảng cách hợp lý.",
        "skill_targets": ["specialization", "knowledge_gap", "application", "analysis"],
    },
    {
        "week_number": 6,
        "title": "Week 6 - Advanced Practice",
        "stage": "THỰC HÀNH NÂNG CAO",
        "goals": [
            "Question khó hơn nhưng vẫn cá nhân hóa",
            "Tăng scenario và problem solving",
            "Thử mini challenge",
        ],
        "question_focus": "Question dạng scenario, debugging, code hoặc mini design.",
        "daily_task_focus": "Task nhiều bước hơn, yêu cầu mô tả cách debug hoặc trade-off.",
        "quest_focus": "Quest mini challenge có minh chứng rõ kết quả.",
        "skill_targets": ["scenario", "debugging", "design", "edge_cases"],
    },
    {
        "week_number": 7,
        "title": "Week 7 - Realistic Assessment",
        "stage": "ĐÁNH GIÁ THỰC TẾ",
        "goals": [
            "Gắn question với real task/project",
            "Đánh giá khả năng áp dụng thực tế",
            "Chuẩn bị dữ liệu final review",
        ],
        "question_focus": "Question gần với case study, project thật và lỗi thực tế.",
        "daily_task_focus": "Task có output giống công việc lab thật, ưu tiên chất lượng và ổn định.",
        "quest_focus": "Quest theo buổi review/coaching hoặc hoạt động thực tế.",
        "skill_targets": ["real_task", "case_study", "project", "reliability"],
    },
    {
        "week_number": 8,
        "title": "Week 8 - Final Review",
        "stage": "TỔNG KẾT 8 TUẦN",
        "goals": [
            "Tổng hợp starting profile và current profile",
            "Đánh giá readiness",
            "Chuẩn bị manager decision",
        ],
        "question_focus": "Question tổng hợp cuối lộ trình, đo application và reasoning.",
        "daily_task_focus": "Task final report, minh chứng kết quả và phần học tiếp theo.",
        "quest_focus": "Quest final review hoặc buổi trao đổi với manager/mentor.",
        "skill_targets": ["readiness", "final_report", "promotion", "next_focus"],
    },
]

COMPLETED_TASK_STATUSES = {TaskStatus.COMPLETED, TaskStatus.APPROVED}
ANSWER_EVIDENCE_STATUSES = {
    QuestionAnswerStatus.AI_REVIEWED,
    QuestionAnswerStatus.APPROVED,
}


class DevelopmentService:
    """Business logic for member development workflows."""

    def _now(self) -> datetime:
        return datetime.now(VN_TIMEZONE).replace(tzinfo=None)

    def _require_manager(self, user: User) -> None:
        if not (user.is_admin() or user.is_mentor()):
            raise ForbiddenException("Manager access required")

    def _default_deadline(self, target_date: date) -> datetime:
        return datetime.combine(target_date, time(23, 59, 59))

    def _coerce_member_level(self, value) -> MemberLevel:
        if isinstance(value, MemberLevel):
            return value
        return MemberLevel(value)

    def _can_have_roadmap(self, user: User) -> bool:
        roles = set(user.roles or [])
        return UserRole.CANDIDATE.value in roles or UserRole.MEMBER.value in roles

    def _roadmap_position(self, started_at: datetime) -> tuple[int, int, float, str]:
        elapsed_days = max(0, (self._now().date() - started_at.date()).days)
        current_day = min(elapsed_days + 1, ROADMAP_TOTAL_DAYS)
        current_week = min(((current_day - 1) // 7) + 1, ROADMAP_TOTAL_WEEKS)
        status = "completed" if elapsed_days >= ROADMAP_TOTAL_DAYS else "active"
        progress = 100.0 if status == "completed" else round((current_week / ROADMAP_TOTAL_WEEKS) * 100.0, 1)
        return current_week, current_day, progress, status

    def _roadmap_template(self, week_number: int) -> Dict[str, object]:
        return ROADMAP_WEEK_TEMPLATES[min(max(week_number, 1), ROADMAP_TOTAL_WEEKS) - 1]

    def _create_roadmap_week(
        self,
        roadmap: MemberRoadmap,
        template: Dict[str, object],
    ) -> MemberRoadmapWeek:
        week_number = int(template["week_number"])
        planned_start_at = roadmap.started_at + timedelta(days=(week_number - 1) * 7)
        planned_end_at = roadmap.started_at + timedelta(days=week_number * 7)
        return MemberRoadmapWeek(
            roadmap_id=roadmap.id,
            week_number=week_number,
            title=str(template["title"]),
            stage=str(template["stage"]),
            goals=list(template["goals"]),
            question_focus=str(template["question_focus"]),
            daily_task_focus=str(template["daily_task_focus"]),
            quest_focus=str(template["quest_focus"]),
            skill_targets=list(template["skill_targets"]),
            planned_start_at=planned_start_at,
            planned_end_at=planned_end_at,
            weekly_evaluation="Chưa bắt đầu.",
        )

    def _coerce_evidence_datetime(self, value) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, time.min)
        return None

    def _is_inside_week(self, value, week: MemberRoadmapWeek) -> bool:
        evidence_at = self._coerce_evidence_datetime(value)
        return bool(evidence_at and week.planned_start_at <= evidence_at < week.planned_end_at)

    def _week_progress(
        self,
        week: MemberRoadmapWeek,
        user_tasks: List[UserTask],
        answers: List[UserQuestionAnswer],
        quests: List[DailyQuest],
    ) -> float:
        if self._now() < week.planned_start_at:
            return 0.0

        week_tasks = [
            task
            for task in user_tasks
            if self._is_inside_week(task.assigned_for_date or task.created_at, week)
        ]
        week_answers = [
            answer
            for answer in answers
            if self._is_inside_week(answer.submitted_at or answer.created_at, week)
        ]
        week_quests = [
            quest
            for quest in quests
            if self._is_inside_week(quest.created_at, week)
        ]

        task_rate = (
            sum(1 for task in week_tasks if task.status in COMPLETED_TASK_STATUSES) / len(week_tasks) * 100.0
            if week_tasks
            else 0.0
        )
        answer_rate = (
            sum(1 for answer in week_answers if answer.status in ANSWER_EVIDENCE_STATUSES or answer.ai_score is not None)
            / len(week_answers)
            * 100.0
            if week_answers
            else 0.0
        )
        quest_rate = (
            sum(1 for quest in week_quests if quest.status == DailyQuestStatus.COMPLETED) / len(week_quests) * 100.0
            if week_quests
            else 0.0
        )
        return round((task_rate + answer_rate + quest_rate) / 3.0, 1)

    def _weekly_evaluation(self, week: MemberRoadmapWeek, progress: float) -> str:
        now = self._now()
        if now < week.planned_start_at:
            return "Chưa bắt đầu."
        if progress >= 80:
            return "Tiến độ tốt. Tiếp tục giữ nhịp học và minh chứng rõ ràng."
        if progress >= 40:
            return "Đang cải thiện. Nên hoàn thiện thêm task/question trong tuần."
        if now >= week.planned_end_at:
            return "Tuần đã qua nhưng evidence còn ít. Cần luyện thêm ở tuần tiếp theo."
        return "Đang thu thập dữ liệu trong tuần hiện tại."

    async def ensure_member_roadmap(self, db: AsyncSession, user: User) -> Optional[dict]:
        if not self._can_have_roadmap(user):
            return None

        roadmap = (
            await db.execute(
                select(MemberRoadmap)
                .options(selectinload(MemberRoadmap.weeks))
                .where(MemberRoadmap.user_id == user.id)
                .limit(1)
            )
        ).scalar_one_or_none()

        if roadmap is None:
            started_at = self._now()
            current_week, current_day, progress, status = self._roadmap_position(started_at)
            template = self._roadmap_template(current_week)
            roadmap = MemberRoadmap(
                user_id=user.id,
                status=status,
                started_at=started_at,
                target_end_at=started_at + timedelta(days=ROADMAP_TOTAL_DAYS),
                current_week=current_week,
                current_day=current_day,
                total_weeks=ROADMAP_TOTAL_WEEKS,
                total_days=ROADMAP_TOTAL_DAYS,
                progress_percentage=progress,
                current_stage=str(template["stage"]),
            )
            db.add(roadmap)
            await db.flush()

        weeks = list(
            (
                await db.execute(
                    select(MemberRoadmapWeek)
                    .where(MemberRoadmapWeek.roadmap_id == roadmap.id)
                    .order_by(MemberRoadmapWeek.week_number)
                )
            ).scalars().all()
        )
        existing_weeks = {week.week_number for week in weeks}
        for template in ROADMAP_WEEK_TEMPLATES:
            if int(template["week_number"]) not in existing_weeks:
                week = self._create_roadmap_week(roadmap, template)
                db.add(week)

        await db.flush()
        weeks = list(
            (
                await db.execute(
                    select(MemberRoadmapWeek)
                    .where(MemberRoadmapWeek.roadmap_id == roadmap.id)
                    .order_by(MemberRoadmapWeek.week_number)
                )
            ).scalars().all()
        )
        set_committed_value(roadmap, "weeks", weeks)
        await self._sync_roadmap_progress(db, user, roadmap)
        return self._roadmap_to_response(roadmap)

    async def _sync_roadmap_progress(
        self,
        db: AsyncSession,
        user: User,
        roadmap: MemberRoadmap,
    ) -> None:
        current_week, current_day, progress, status = self._roadmap_position(roadmap.started_at)
        template = self._roadmap_template(current_week)
        roadmap.current_week = current_week
        roadmap.current_day = current_day
        roadmap.progress_percentage = progress
        roadmap.status = status
        roadmap.current_stage = str(template["stage"])
        roadmap.updated_at = self._now()

        user_tasks = list(
            (
                await db.execute(select(UserTask).where(UserTask.user_id == user.id))
            ).scalars().all()
        )
        answers = list(
            (
                await db.execute(select(UserQuestionAnswer).where(UserQuestionAnswer.user_id == user.id))
            ).scalars().all()
        )
        quests = list(
            (
                await db.execute(select(DailyQuest).where(DailyQuest.user_id == user.id))
            ).scalars().all()
        )

        for week in roadmap.weeks:
            week.progress_percentage = self._week_progress(week, user_tasks, answers, quests)
            week.weekly_evaluation = self._weekly_evaluation(week, week.progress_percentage)
            week.updated_at = self._now()

    def _roadmap_to_response(self, roadmap: MemberRoadmap) -> dict:
        weeks = sorted(roadmap.weeks, key=lambda item: item.week_number)
        return {
            "id": roadmap.id,
            "user_id": roadmap.user_id,
            "status": roadmap.status,
            "started_at": roadmap.started_at,
            "target_end_at": roadmap.target_end_at,
            "current_week": roadmap.current_week,
            "current_day": roadmap.current_day,
            "total_weeks": roadmap.total_weeks,
            "total_days": roadmap.total_days,
            "progress_percentage": round(float(roadmap.progress_percentage or 0.0), 1),
            "current_stage": roadmap.current_stage,
            "weeks": [
                {
                    "id": week.id,
                    "week_number": week.week_number,
                    "title": week.title,
                    "stage": week.stage,
                    "goals": list(week.goals or []),
                    "question_focus": week.question_focus,
                    "daily_task_focus": week.daily_task_focus,
                    "quest_focus": week.quest_focus,
                    "skill_targets": list(week.skill_targets or []),
                    "progress_percentage": round(float(week.progress_percentage or 0.0), 1),
                    "weekly_evaluation": week.weekly_evaluation,
                    "planned_start_at": week.planned_start_at,
                    "planned_end_at": week.planned_end_at,
                    "is_current": roadmap.status == "active" and week.week_number == roadmap.current_week,
                    "is_completed": roadmap.status == "completed" or week.week_number < roadmap.current_week,
                }
                for week in weeks
            ],
        }

    def _fallback_score_submission(self, user_task: UserTask) -> tuple[float, str]:
        text = f"{user_task.submission_notes or ''} {user_task.proof_link or ''}".strip()
        evidence_count = len(user_task.evidence_links or [])
        base = 40.0 + (len(text.split()) * 2.0) + (evidence_count * 8.0)
        if user_task.proof_link:
            base += 15.0
        if user_task.completion_percentage:
            base = (base * 0.6) + (user_task.completion_percentage * 0.4)
        score = round(min(max(base, 0.0), 100.0), 1)

        if score >= 85:
            feedback = "AI gợi ý bài làm đủ tốt; quản lý vẫn cần kiểm tra trước khi chốt điểm."
        elif score >= 60:
            feedback = "AI gợi ý bài làm có tiến triển, nên bổ sung minh chứng hoặc giải thích rõ hơn."
        else:
            feedback = "AI gợi ý bài làm còn thiếu dữ liệu để đánh giá chắc chắn."
        return score, feedback

    async def _score_submission(self, user_task: UserTask) -> tuple[float, str]:
        task = user_task.task
        system_prompt = (
            "Bạn là AI reviewer của TLMS. Chấm bài nộp daily task theo thang 0-100 dựa trên mô tả task, "
            "mức hoàn thành và minh chứng người dùng đã nộp. Trả về đúng JSON: "
            "{\"score\": number, \"feedback\": string}."
        )
        user_prompt = json.dumps(
            {
                "task": {
                    "title": task.title if task else None,
                    "description": task.description if task else None,
                    "instructions": task.instructions if task else None,
                    "difficulty": getattr(task.difficulty, "value", task.difficulty) if task else None,
                    "xp_reward": task.xp_reward if task else None,
                },
                "submission": {
                    "proof_link": user_task.proof_link,
                    "submission_notes": user_task.submission_notes,
                    "completion_percentage": user_task.completion_percentage,
                    "evidence_links": user_task.evidence_links or [],
                },
            },
            ensure_ascii=False,
        )
        try:
            result = await ai_json_service.generate_json(system_prompt, user_prompt, max_tokens=500, temperature=0.1)
            score = round(float(result.get("score", 0)), 1)
            score = min(max(score, 0.0), 100.0)
            feedback = str(result.get("feedback") or "").strip()
            return score, feedback or "AI đã chấm bài nộp."
        except Exception as exc:
            logger.warning("Task AI scoring failed for %s: %s", user_task.id, exc)
            return self._fallback_score_submission(user_task)

    async def assign_daily_tasks(
        self,
        db: AsyncSession,
        manager: User,
        request: DailyTaskAssignRequest,
    ) -> dict:
        self._require_manager(manager)

        target_date = request.target_date or date.today()
        deadline_at = request.deadline_at or self._default_deadline(target_date)
        target_level = self._coerce_member_level(request.target_member_level)

        task_query = select(Task).where(
            Task.is_active == True,
            Task.target_member_level == target_level,
        )

        if request.task_ids:
            task_query = task_query.where(Task.id.in_(request.task_ids))
        else:
            allowed_difficulties = [TaskDifficulty.EASY, TaskDifficulty.MEDIUM]
            if target_level == MemberLevel.DILIGENT:
                allowed_difficulties = [TaskDifficulty.MEDIUM, TaskDifficulty.HARD, TaskDifficulty.ADVANCED]
            elif target_level == MemberLevel.OFFICIAL:
                allowed_difficulties = [TaskDifficulty.HARD, TaskDifficulty.ADVANCED, TaskDifficulty.EXPERT]
            task_query = task_query.where(Task.difficulty.in_(allowed_difficulties))

        if not request.include_ai_tasks:
            task_query = task_query.where(Task.creator_type != TaskCreatorType.AI)

        task_query = task_query.order_by(Task.order_index, Task.created_at).limit(request.tasks_per_member)
        tasks = list((await db.execute(task_query)).scalars().all())
        if not tasks:
            raise BadRequestException("No active tasks match the daily assignment criteria")

        if target_level == MemberLevel.OFFICIAL:
            non_ai_tasks = [task for task in tasks if task.creator_type != TaskCreatorType.AI]
            skipped_official_ai = len(tasks) - len(non_ai_tasks)
            tasks = non_ai_tasks
        else:
            skipped_official_ai = 0

        if not tasks:
            raise BadRequestException("Official members cannot receive automatic AI tasks")

        user_query = select(User).where(User.status == UserStatus.ACTIVE)
        if request.user_ids:
            user_query = user_query.where(User.id.in_(request.user_ids))
        else:
            user_query = user_query.where(
                User.member_level == target_level,
                ~User.roles.contains([UserRole.ADMIN.value]),
                ~User.roles.contains([UserRole.MENTOR.value]),
            )

        users = list((await db.execute(user_query)).scalars().all())
        assignments_created = 0
        skipped_existing = 0

        for user in users:
            eligible_tasks = [
                task for task in tasks
                if not (user.member_level == MemberLevel.OFFICIAL and task.creator_type == TaskCreatorType.AI)
            ]
            skipped_official_ai += len(tasks) - len(eligible_tasks)

            created_for_user = 0
            for task in eligible_tasks:
                existing = (
                    await db.execute(
                        select(UserTask).where(
                            UserTask.user_id == user.id,
                            UserTask.task_id == task.id,
                            UserTask.assigned_for_date == target_date,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    skipped_existing += 1
                    continue

                user_task = UserTask(
                    user_id=user.id,
                    task_id=task.id,
                    status=TaskStatus.AVAILABLE,
                    assigned_for_date=target_date,
                    deadline_at=deadline_at,
                    assigned_by_id=manager.id,
                    needs_manager_review=task.requires_manager_review,
                )
                db.add(user_task)
                assignments_created += 1
                created_for_user += 1

            if created_for_user:
                await notification_service.create_notification(
                    db,
                    user_id=user.id,
                    event_type="NEW_TASK",
                    title="Bạn vừa nhận Daily Task mới",
                    message=f"Bạn có {created_for_user} task cho ngày {target_date.isoformat()}.",
                    actor_id=manager.id,
                    payload={"target_date": target_date.isoformat(), "count": created_for_user},
                )

        await db.commit()

        return {
            "target_date": target_date,
            "target_member_level": target_level,
            "users_considered": len(users),
            "tasks_considered": len(tasks),
            "assignments_created": assignments_created,
            "skipped_existing": skipped_existing,
            "skipped_official_ai": skipped_official_ai,
        }

    async def update_task_progress(
        self,
        db: AsyncSession,
        user: User,
        user_task_id: UUID,
        progress_percentage: float,
        notes: Optional[str],
    ) -> UserTask:
        user_task = (
            await db.execute(
                select(UserTask)
                .options(selectinload(UserTask.task))
                .where(UserTask.id == user_task_id, UserTask.user_id == user.id)
            )
        ).scalar_one_or_none()
        if not user_task:
            raise NotFoundException("Task not found")
        if user_task.status in [TaskStatus.COMPLETED, TaskStatus.APPROVED]:
            raise BadRequestException("Completed tasks cannot be updated")

        user_task.progress_percentage = progress_percentage
        user_task.updated_at = datetime.utcnow()
        db.add(
            TaskProgressUpdate(
                user_task_id=user_task.id,
                user_id=user.id,
                progress_percentage=progress_percentage,
                notes=notes,
            )
        )

        await db.commit()
        await db.refresh(user_task)
        return user_task

    async def apply_ai_submission_review(self, db: AsyncSession, user_task: UserTask) -> None:
        ai_score, ai_feedback = await self._score_submission(user_task)
        user_task.ai_score = ai_score
        user_task.ai_feedback = ai_feedback
        pass_score = get_settings().AI_AUTO_PASS_SCORE
        should_auto_finalize = user_task.assigned_for_date is not None or not user_task.needs_manager_review

        if should_auto_finalize:
            user_task.final_score = ai_score
            user_task.reviewed_at = datetime.utcnow()
            user_task.final_feedback = ai_feedback
            if ai_score >= pass_score:
                user_task.status = TaskStatus.COMPLETED
                user_task.xp_earned = user_task.task.xp_reward if user_task.task else 0
                user_task.completed_at = datetime.utcnow()
                user_task.completion_percentage = max(user_task.completion_percentage or 0.0, 100.0)
                user_task.progress_percentage = 100.0
                if user_task.user and (
                    user_task.user.has_role(UserRole.CANDIDATE.value)
                    or user_task.user.has_role(UserRole.MEMBER.value)
                ):
                    user_task.user.current_xp += user_task.xp_earned
                    user_task.user.level = user_task.user.calculate_level()
            else:
                user_task.status = TaskStatus.REJECTED
                user_task.mentor_comment = ai_feedback
        else:
            user_task.status = TaskStatus.AI_REVIEWED

        await notification_service.create_notification(
            db,
            user_id=user_task.user_id,
            event_type="TASK_SCORED",
            title="AI đã chấm task",
            message=ai_feedback,
            payload={
                "user_task_id": str(user_task.id),
                "ai_score": ai_score,
                "auto_finalized": should_auto_finalize,
                "passed": ai_score >= pass_score,
            },
        )

    async def reconcile_daily_tasks(
        self,
        db: AsyncSession,
        manager: User,
        target_date: Optional[date] = None,
        user_ids: Optional[List[UUID]] = None,
    ) -> tuple[date, List[DailyTaskReport]]:
        self._require_manager(manager)

        resolved_date = target_date or date.today()
        user_query = select(User).where(User.status == UserStatus.ACTIVE)
        if user_ids:
            user_query = user_query.where(User.id.in_(user_ids))
        else:
            user_query = user_query.where(
                ~User.roles.contains([UserRole.ADMIN.value]),
                ~User.roles.contains([UserRole.MENTOR.value]),
            )

        users = list((await db.execute(user_query)).scalars().all())
        reports: List[DailyTaskReport] = []

        for user in users:
            report = await self._reconcile_user_daily_tasks(db, user, resolved_date)
            reports.append(report)

        await db.commit()
        return resolved_date, reports

    async def _reconcile_user_daily_tasks(
        self,
        db: AsyncSession,
        user: User,
        target_date: date,
    ) -> DailyTaskReport:
        settings = get_settings()
        now = datetime.utcnow()

        user_tasks = list(
            (
                await db.execute(
                    select(UserTask)
                    .options(selectinload(UserTask.task))
                    .where(
                        UserTask.user_id == user.id,
                        UserTask.assigned_for_date == target_date,
                    )
                )
            ).scalars().all()
        )

        for user_task in user_tasks:
            if (
                user_task.deadline_at
                and user_task.deadline_at < now
                and user_task.status in [TaskStatus.AVAILABLE, TaskStatus.IN_PROGRESS]
            ):
                user_task.status = TaskStatus.MISSED

        assigned_count = len(user_tasks)
        completed_count = sum(1 for task in user_tasks if task.status in [TaskStatus.COMPLETED, TaskStatus.APPROVED])
        late_count = sum(1 for task in user_tasks if task.status == TaskStatus.LATE)
        missed_count = sum(1 for task in user_tasks if task.status == TaskStatus.MISSED)
        completion_rate = round((completed_count / assigned_count * 100.0), 1) if assigned_count else 0.0

        if assigned_count and completion_rate >= settings.DAILY_TASK_COMPLETE_THRESHOLD * 100:
            attendance_status = DailyTaskStatus.COMPLETE
            discipline_delta = settings.DAILY_DISCIPLINE_COMPLETE_BONUS
            reliability_delta = settings.DAILY_RELIABILITY_COMPLETE_BONUS
        elif assigned_count and completion_rate >= settings.DAILY_TASK_PARTIAL_THRESHOLD * 100:
            attendance_status = DailyTaskStatus.PARTIAL
            discipline_delta = settings.DAILY_DISCIPLINE_PARTIAL_PENALTY
            reliability_delta = settings.DAILY_RELIABILITY_PARTIAL_PENALTY
        elif assigned_count:
            attendance_status = DailyTaskStatus.MISSED
            discipline_delta = settings.DAILY_DISCIPLINE_MISSED_PENALTY
            reliability_delta = settings.DAILY_RELIABILITY_MISSED_PENALTY
        else:
            attendance_status = DailyTaskStatus.MISSED
            discipline_delta = 0.0
            reliability_delta = 0.0

        report = (
            await db.execute(
                select(DailyTaskReport).where(
                    DailyTaskReport.user_id == user.id,
                    DailyTaskReport.report_date == target_date,
                )
            )
        ).scalar_one_or_none()

        previous_discipline_delta = report.discipline_delta if report else 0.0
        previous_reliability_delta = report.reliability_delta if report else 0.0

        if report is None:
            report = DailyTaskReport(user_id=user.id, report_date=target_date)
            db.add(report)

        report.assigned_count = assigned_count
        report.completed_count = completed_count
        report.late_count = late_count
        report.missed_count = missed_count
        report.completion_rate = completion_rate
        report.attendance_status = attendance_status
        report.discipline_delta = discipline_delta
        report.reliability_delta = reliability_delta
        report.recalculated_at = now

        user.discipline_score = min(100.0, max(0.0, user.discipline_score - previous_discipline_delta + discipline_delta))
        user.reliability_score = min(100.0, max(0.0, user.reliability_score - previous_reliability_delta + reliability_delta))

        await self.evaluate_member(db, user, created_by=None, commit=False)
        await self.ensure_promotion_eligibility(db, user)

        return report

    async def evaluate_member(
        self,
        db: AsyncSession,
        user: User,
        created_by: Optional[User] = None,
        manager_score: Optional[float] = None,
        notes: Optional[str] = None,
        commit: bool = True,
    ) -> MemberEvaluation:
        settings = get_settings()

        task_rows = list(
            (
                await db.execute(select(UserTask).where(UserTask.user_id == user.id))
            ).scalars().all()
        )
        total_tasks = len(task_rows)
        completed_tasks = sum(1 for task in task_rows if task.status in [TaskStatus.COMPLETED, TaskStatus.APPROVED])
        task_completion_rate = (completed_tasks / total_tasks * 100.0) if total_tasks else 0.0

        scored_tasks = [
            task.final_score if task.final_score is not None else task.manager_score if task.manager_score is not None else task.ai_score
            for task in task_rows
            if task.final_score is not None or task.manager_score is not None or task.ai_score is not None
        ]
        task_quality_score = (sum(scored_tasks) / len(scored_tasks)) if scored_tasks else task_completion_rate

        reports = list(
            (
                await db.execute(select(DailyTaskReport).where(DailyTaskReport.user_id == user.id))
            ).scalars().all()
        )
        attendance_score = (sum(report.completion_rate for report in reports) / len(reports)) if reports else 0.0
        activity_days = len({task.created_at.date() for task in task_rows})
        activity_score = min(100.0, activity_days * 10.0)

        final_score = (
            task_completion_rate * settings.MEMBER_EVALUATION_TASK_WEIGHT
            + task_quality_score * settings.MEMBER_EVALUATION_QUALITY_WEIGHT
            + attendance_score * settings.MEMBER_EVALUATION_ATTENDANCE_WEIGHT
            + user.discipline_score * settings.MEMBER_EVALUATION_DISCIPLINE_WEIGHT
        )

        if manager_score is not None:
            final_score = (final_score * 0.7) + (manager_score * 0.3)

        final_score = round(min(max(final_score, 0.0), 100.0), 1)

        evaluation = MemberEvaluation(
            user_id=user.id,
            task_completion_rate=round(task_completion_rate, 1),
            task_quality_score=round(task_quality_score, 1),
            attendance_score=round(attendance_score, 1),
            discipline_score=round(user.discipline_score, 1),
            activity_score=round(activity_score, 1),
            manager_score=manager_score,
            final_score=final_score,
            notes=notes,
            created_by_id=created_by.id if created_by else None,
        )
        db.add(evaluation)

        user.member_score = final_score
        user.promotion_progress = self._calculate_promotion_progress(
            attendance_score=attendance_score,
            task_completion_rate=task_completion_rate,
            member_score=final_score,
        )
        user.is_ready_to_promote = user.promotion_progress >= 100.0 and user.member_level != MemberLevel.OFFICIAL

        if commit:
            await self.ensure_promotion_eligibility(db, user)
            await db.commit()
            await db.refresh(evaluation)

        return evaluation

    def _calculate_promotion_progress(
        self,
        attendance_score: float,
        task_completion_rate: float,
        member_score: float,
    ) -> float:
        settings = get_settings()
        attendance_progress = min(attendance_score / settings.PROMOTION_ATTENDANCE_THRESHOLD, 1.0)
        task_progress = min(task_completion_rate / settings.PROMOTION_TASK_COMPLETION_THRESHOLD, 1.0)
        score_progress = min(member_score / settings.PROMOTION_SCORE_THRESHOLD, 1.0)
        return round(((attendance_progress + task_progress + score_progress) / 3.0) * 100.0, 1)

    async def ensure_promotion_eligibility(self, db: AsyncSession, user: User) -> Optional[PromotionReview]:
        if user.member_level == MemberLevel.OFFICIAL or not user.is_ready_to_promote:
            return None

        target_level = NEXT_MEMBER_LEVEL.get(user.member_level)
        if not target_level:
            return None

        existing = (
            await db.execute(
                select(PromotionReview).where(
                    PromotionReview.user_id == user.id,
                    PromotionReview.from_member_level == user.member_level,
                    PromotionReview.to_member_level == target_level,
                    PromotionReview.status.in_([PromotionStatus.ELIGIBLE, PromotionStatus.PENDING]),
                )
            )
        ).scalar_one_or_none()

        metrics = {
            "promotion_progress": user.promotion_progress,
            "member_score": user.member_score,
            "discipline_score": user.discipline_score,
            "reliability_score": user.reliability_score,
            "current_xp": user.current_xp,
        }

        if existing:
            existing.metrics = metrics
            existing.updated_at = datetime.utcnow()
            return existing

        review = PromotionReview(
            user_id=user.id,
            from_member_level=user.member_level,
            to_member_level=target_level,
            status=PromotionStatus.ELIGIBLE,
            metrics=metrics,
        )
        db.add(review)
        await notification_service.create_notification(
            db,
            user_id=user.id,
            event_type="PROMOTION_ELIGIBLE",
            title="Bạn đủ điều kiện xét nâng cấp",
            message="Hồ sơ của bạn đã được đưa vào danh sách chờ quản lý xem xét.",
            payload={"to_member_level": target_level.value},
        )
        return review

    async def list_promotions(
        self,
        db: AsyncSession,
        manager: User,
        status: Optional[PromotionStatus] = None,
    ) -> List[PromotionReview]:
        self._require_manager(manager)
        query = select(PromotionReview).options(selectinload(PromotionReview.user))
        if status:
            query = query.where(PromotionReview.status == status)
        query = query.order_by(PromotionReview.created_at.desc())
        return list((await db.execute(query)).scalars().all())

    async def decide_promotion(
        self,
        db: AsyncSession,
        manager: User,
        review_id: UUID,
        approved: bool,
        notes: Optional[str] = None,
    ) -> PromotionReview:
        self._require_manager(manager)

        review = (
            await db.execute(
                select(PromotionReview)
                .options(selectinload(PromotionReview.user))
                .where(PromotionReview.id == review_id)
            )
        ).scalar_one_or_none()
        if not review:
            raise NotFoundException("Promotion review not found")
        if review.status in [PromotionStatus.APPROVED, PromotionStatus.REJECTED]:
            raise BadRequestException("Promotion review already decided")

        review.manager_id = manager.id
        review.manager_notes = notes
        review.decided_at = datetime.utcnow()
        review.updated_at = datetime.utcnow()

        if approved:
            review.status = PromotionStatus.APPROVED
            review.user.member_level = review.to_member_level
            review.user.is_ready_to_promote = False
            review.user.promotion_progress = 0.0
            event_type = "PROMOTION_APPROVED"
            title = "Yêu cầu nâng cấp đã được duyệt"
            message = f"Bạn đã được nâng lên cấp {review.to_member_level.value}."
        else:
            review.status = PromotionStatus.REJECTED
            review.user.is_ready_to_promote = False
            event_type = "PROMOTION_REJECTED"
            title = "Yêu cầu nâng cấp chưa được duyệt"
            message = notes or "Quản lý đã từ chối yêu cầu nâng cấp ở lần đánh giá này."

        await notification_service.create_notification(
            db,
            user_id=review.user_id,
            event_type=event_type,
            title=title,
            message=message,
            actor_id=manager.id,
            payload={"promotion_review_id": str(review.id)},
        )

        await db.commit()
        review = (
            await db.execute(
                select(PromotionReview)
                .options(selectinload(PromotionReview.user))
                .where(PromotionReview.id == review_id)
            )
        ).scalar_one()
        return review

    async def get_member_dashboard(self, db: AsyncSession, user: User) -> dict:
        roadmap = await self.ensure_member_roadmap(db, user)
        today = date.today()
        today_tasks = list(
            (
                await db.execute(
                    select(UserTask)
                    .options(selectinload(UserTask.task).selectinload(Task.creator))
                    .where(UserTask.user_id == user.id, UserTask.assigned_for_date == today)
                    .order_by(UserTask.deadline_at, UserTask.created_at)
                )
            ).scalars().all()
        )
        assigned_tasks = list(
            (
                await db.execute(
                    select(UserTask)
                    .options(selectinload(UserTask.task).selectinload(Task.creator))
                    .where(
                        UserTask.user_id == user.id,
                        UserTask.assigned_for_date.is_(None),
                        UserTask.status.in_([
                            TaskStatus.AVAILABLE,
                            TaskStatus.IN_PROGRESS,
                            TaskStatus.SUBMITTED,
                            TaskStatus.AI_REVIEWED,
                            TaskStatus.REJECTED,
                        ]),
                    )
                    .order_by(UserTask.deadline_at, UserTask.created_at.desc())
                )
            ).scalars().all()
        )

        report = (
            await db.execute(
                select(DailyTaskReport).where(
                    DailyTaskReport.user_id == user.id,
                    DailyTaskReport.report_date == today,
                )
            )
        ).scalar_one_or_none()

        completed_tasks = sum(1 for task in today_tasks if task.status in [TaskStatus.COMPLETED, TaskStatus.APPROVED])
        pending_tasks = sum(1 for task in today_tasks if task.status not in [TaskStatus.COMPLETED, TaskStatus.APPROVED])
        daily_completion_rate = round((completed_tasks / len(today_tasks) * 100.0), 1) if today_tasks else 0.0

        notifications = list(
            (
                await db.execute(
                    select(Notification)
                    .where(Notification.user_id == user.id)
                    .order_by(Notification.created_at.desc())
                    .limit(5)
                )
            ).scalars().all()
        )
        unread_count = (
            await db.execute(
                select(func.count(Notification.id)).where(
                    Notification.user_id == user.id,
                    Notification.read_at.is_(None),
                )
            )
        ).scalar() or 0
        achievements = await achievement_service.get_dashboard(db, user)

        return {
            "member_level": user.member_level,
            "current_xp": user.current_xp,
            "level": user.level,
            "discipline_score": user.discipline_score,
            "reliability_score": user.reliability_score,
            "member_score": user.member_score,
            "promotion_progress": user.promotion_progress,
            "today_tasks": today_tasks,
            "assigned_tasks": assigned_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "daily_completion_rate": daily_completion_rate,
            "attendance_status": report.attendance_status if report else None,
            "promotion_eligible": user.is_ready_to_promote,
            "unread_notifications": unread_count,
            "notifications": notifications,
            "roadmap": roadmap,
            "achievements": achievements,
        }

    async def get_manager_summary(self, db: AsyncSession, manager: User) -> dict:
        self._require_manager(manager)
        today = date.today()

        total_members = (
            await db.execute(
                select(func.count(User.id)).where(
                    User.status == UserStatus.ACTIVE,
                    ~User.roles.contains([UserRole.ADMIN.value]),
                    ~User.roles.contains([UserRole.MENTOR.value]),
                )
            )
        ).scalar() or 0

        counts_by_level = {}
        for member_level in MemberLevel:
            counts_by_level[member_level] = (
                await db.execute(
                    select(func.count(User.id)).where(
                        User.status == UserStatus.ACTIVE,
                        User.member_level == member_level,
                        ~User.roles.contains([UserRole.ADMIN.value]),
                        ~User.roles.contains([UserRole.MENTOR.value]),
                    )
                )
            ).scalar() or 0

        today_tasks = list(
            (
                await db.execute(select(UserTask).where(UserTask.assigned_for_date == today))
            ).scalars().all()
        )
        completed_today = sum(1 for task in today_tasks if task.status in [TaskStatus.COMPLETED, TaskStatus.APPROVED])
        daily_task_completion = round((completed_today / len(today_tasks) * 100.0), 1) if today_tasks else 0.0
        missed_tasks = sum(1 for task in today_tasks if task.status == TaskStatus.MISSED)

        pending_reviews = (
            await db.execute(
                select(func.count(UserTask.id)).where(
                    UserTask.status.in_([TaskStatus.SUBMITTED, TaskStatus.AI_REVIEWED, TaskStatus.LATE])
                )
            )
        ).scalar() or 0

        promotion_eligible = (
            await db.execute(
                select(func.count(PromotionReview.id)).where(
                    PromotionReview.status.in_([PromotionStatus.ELIGIBLE, PromotionStatus.PENDING])
                )
            )
        ).scalar() or 0

        average_completion_rate = (
            await db.execute(select(func.avg(DailyTaskReport.completion_rate)))
        ).scalar() or 0.0

        active_members = (
            await db.execute(
                select(func.count(func.distinct(UserTask.user_id))).where(
                    UserTask.updated_at >= datetime.combine(today, time.min)
                )
            )
        ).scalar() or 0

        return {
            "total_members": total_members,
            "new_members": counts_by_level.get(MemberLevel.NEW, 0),
            "diligent_members": counts_by_level.get(MemberLevel.DILIGENT, 0),
            "official_members": counts_by_level.get(MemberLevel.OFFICIAL, 0),
            "daily_task_completion": daily_task_completion,
            "missed_tasks": missed_tasks,
            "pending_reviews": pending_reviews,
            "promotion_eligible": promotion_eligible,
            "average_completion_rate": round(float(average_completion_rate), 1),
            "active_members": active_members,
        }


development_service = DevelopmentService()
