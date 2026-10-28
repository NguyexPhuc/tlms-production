"""Achievement badge catalog and unlock logic."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.development import (
    AchievementBadge,
    DailyTaskReport,
    DailyTaskStatus,
    Question,
    QuestionAnswerStatus,
    UserAchievementBadge,
    UserQuestionAnswer,
)
from app.models.profile import EvidenceStatus, ProfileEvidence
from app.models.quest import DailyQuest, DailyQuestStatus, DailyQuestType
from app.models.task import Task, TaskStatus, TaskType, UserTask
from app.models.user import User


BADGE_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "code": "xp_100",
        "title": "Mở màn",
        "description": "Đạt 100 XP đầu tiên trong TLMS.",
        "category": "xp",
        "metric": "current_xp",
        "target_value": 100,
        "badge_icon": "XP",
        "badge_color": "#1E90FF",
        "sort_order": 10,
    },
    {
        "code": "xp_500",
        "title": "Bứt tốc",
        "description": "Tích lũy 500 XP từ task, quest và câu hỏi.",
        "category": "xp",
        "metric": "current_xp",
        "target_value": 500,
        "badge_icon": "500",
        "badge_color": "#9333ea",
        "sort_order": 20,
    },
    {
        "code": "level_3",
        "title": "Lên cấp",
        "description": "Chạm Level 3 bằng tiến độ học tập ổn định.",
        "category": "xp",
        "metric": "level",
        "target_value": 3,
        "badge_icon": "L3",
        "badge_color": "#0ea5e9",
        "sort_order": 30,
    },
    {
        "code": "task_first",
        "title": "Task đầu",
        "description": "Hoàn thành task đầu tiên được giao.",
        "category": "task",
        "metric": "completed_tasks",
        "target_value": 1,
        "badge_icon": "T1",
        "badge_color": "#32CD32",
        "sort_order": 40,
    },
    {
        "code": "task_5",
        "title": "Task 5",
        "description": "Hoàn thành 5 task để chứng minh nhịp làm việc ổn định.",
        "category": "task",
        "metric": "completed_tasks",
        "target_value": 5,
        "badge_icon": "T5",
        "badge_color": "#16a34a",
        "sort_order": 50,
    },
    {
        "code": "core_3",
        "title": "Core 3",
        "description": "Hoàn thành 3 Core Task bắt buộc của lộ trình.",
        "category": "task",
        "metric": "completed_core_tasks",
        "target_value": 3,
        "badge_icon": "CT",
        "badge_color": "#dc2626",
        "sort_order": 60,
    },
    {
        "code": "baseline_ready",
        "title": "Test IT",
        "description": "Trả lời đủ bộ câu hỏi SQL, Backend và Frontend.",
        "category": "question",
        "metric": "baseline_answers",
        "target_value": 3,
        "badge_icon": "IT",
        "badge_color": "#6366f1",
        "sort_order": 70,
    },
    {
        "code": "question_5",
        "title": "Tư duy",
        "description": "Hoàn thành 5 câu hỏi đánh giá năng lực kỹ thuật.",
        "category": "question",
        "metric": "question_answers",
        "target_value": 5,
        "badge_icon": "Q5",
        "badge_color": "#7c3aed",
        "sort_order": 80,
    },
    {
        "code": "daily_quest_first",
        "title": "Daily 1",
        "description": "Hoàn thành Daily Quest đầu tiên trong ngày.",
        "category": "quest",
        "metric": "completed_daily_quests",
        "target_value": 1,
        "badge_icon": "DQ",
        "badge_color": "#f59e0b",
        "sort_order": 90,
    },
    {
        "code": "daily_quest_10",
        "title": "10 Daily Quest",
        "description": "Hoàn thành 10 Daily Quest để tạo thói quen luyện tập.",
        "category": "quest",
        "metric": "completed_daily_quests",
        "target_value": 10,
        "badge_icon": "10",
        "badge_color": "#ea580c",
        "sort_order": 100,
    },
    {
        "code": "limit_quest_first",
        "title": "Offline",
        "description": "Hoàn thành 1 Limit Quest như coaching 1:1 hoặc họp offline.",
        "category": "quest",
        "metric": "completed_limit_quests",
        "target_value": 1,
        "badge_icon": "LQ",
        "badge_color": "#0f766e",
        "sort_order": 110,
    },
    {
        "code": "evidence_first",
        "title": "Minh chứng",
        "description": "Có 1 minh chứng trong profile được xác nhận.",
        "category": "profile",
        "metric": "verified_evidence",
        "target_value": 1,
        "badge_icon": "EV",
        "badge_color": "#0891b2",
        "sort_order": 120,
    },
    {
        "code": "discipline_100",
        "title": "Kỷ luật",
        "description": "Giữ điểm kỷ luật ở mức 100.",
        "category": "discipline",
        "metric": "discipline_score",
        "target_value": 100,
        "badge_icon": "DS",
        "badge_color": "#22c55e",
        "sort_order": 130,
    },
    {
        "code": "attendance_7",
        "title": "7 ngày",
        "description": "Có 7 ngày daily task được ghi nhận hoàn thành đầy đủ.",
        "category": "discipline",
        "metric": "complete_daily_reports",
        "target_value": 7,
        "badge_icon": "7D",
        "badge_color": "#84cc16",
        "sort_order": 140,
    },
]


class AchievementService:
    """Seed badge catalog, calculate progress, and unlock achieved badges."""

    async def ensure_catalog(self, db: AsyncSession) -> List[AchievementBadge]:
        result = await db.execute(select(AchievementBadge))
        existing_by_code = {badge.code: badge for badge in result.scalars().all()}

        for item in BADGE_DEFINITIONS:
            badge = existing_by_code.get(item["code"])
            if badge is None:
                badge = AchievementBadge(**item)
                db.add(badge)
                existing_by_code[item["code"]] = badge
                continue

            for key, value in item.items():
                setattr(badge, key, value)
            badge.updated_at = datetime.utcnow()

        await db.flush()
        return sorted(existing_by_code.values(), key=lambda badge: badge.sort_order)

    async def _count_completed_tasks(self, db: AsyncSession, user: User) -> int:
        return (
            await db.execute(
                select(func.count(UserTask.id)).where(
                    UserTask.user_id == user.id,
                    UserTask.status.in_([TaskStatus.COMPLETED, TaskStatus.APPROVED]),
                )
            )
        ).scalar() or 0

    async def _count_completed_core_tasks(self, db: AsyncSession, user: User) -> int:
        return (
            await db.execute(
                select(func.count(UserTask.id))
                .join(Task, UserTask.task_id == Task.id)
                .where(
                    UserTask.user_id == user.id,
                    UserTask.status.in_([TaskStatus.COMPLETED, TaskStatus.APPROVED]),
                    Task.type == TaskType.CORE,
                )
            )
        ).scalar() or 0

    async def _count_quests(self, db: AsyncSession, user: User, quest_type: DailyQuestType) -> int:
        return (
            await db.execute(
                select(func.count(DailyQuest.id)).where(
                    DailyQuest.user_id == user.id,
                    DailyQuest.quest_type == quest_type,
                    DailyQuest.status == DailyQuestStatus.COMPLETED,
                )
            )
        ).scalar() or 0

    async def _count_question_answers(self, db: AsyncSession, user: User) -> int:
        return (
            await db.execute(
                select(func.count(UserQuestionAnswer.id)).where(
                    UserQuestionAnswer.user_id == user.id,
                    UserQuestionAnswer.status.in_(
                        [
                            QuestionAnswerStatus.AI_REVIEWED,
                            QuestionAnswerStatus.APPROVED,
                        ]
                    ),
                )
            )
        ).scalar() or 0

    async def _count_baseline_answers(self, db: AsyncSession, user: User) -> int:
        return (
            await db.execute(
                select(func.count(UserQuestionAnswer.id))
                .join(Question, UserQuestionAnswer.question_id == Question.id)
                .where(
                    UserQuestionAnswer.user_id == user.id,
                    Question.is_baseline.is_(True),
                    UserQuestionAnswer.status.in_(
                        [
                            QuestionAnswerStatus.AI_REVIEWED,
                            QuestionAnswerStatus.APPROVED,
                        ]
                    ),
                )
            )
        ).scalar() or 0

    async def _count_verified_evidence(self, db: AsyncSession, user: User) -> int:
        return (
            await db.execute(
                select(func.count(ProfileEvidence.id)).where(
                    ProfileEvidence.user_id == user.id,
                    ProfileEvidence.status == EvidenceStatus.VERIFIED,
                )
            )
        ).scalar() or 0

    async def _count_complete_daily_reports(self, db: AsyncSession, user: User) -> int:
        return (
            await db.execute(
                select(func.count(DailyTaskReport.id)).where(
                    DailyTaskReport.user_id == user.id,
                    DailyTaskReport.attendance_status == DailyTaskStatus.COMPLETE,
                )
            )
        ).scalar() or 0

    async def _metric_values(self, db: AsyncSession, user: User) -> Dict[str, float]:
        return {
            "current_xp": float(user.current_xp or 0),
            "level": float(user.calculate_level()),
            "discipline_score": float(user.discipline_score or 0),
            "completed_tasks": float(await self._count_completed_tasks(db, user)),
            "completed_core_tasks": float(await self._count_completed_core_tasks(db, user)),
            "completed_daily_quests": float(await self._count_quests(db, user, DailyQuestType.DAILY)),
            "completed_limit_quests": float(await self._count_quests(db, user, DailyQuestType.LIMIT)),
            "question_answers": float(await self._count_question_answers(db, user)),
            "baseline_answers": float(await self._count_baseline_answers(db, user)),
            "verified_evidence": float(await self._count_verified_evidence(db, user)),
            "complete_daily_reports": float(await self._count_complete_daily_reports(db, user)),
        }

    async def get_dashboard(self, db: AsyncSession, user: User) -> Dict[str, Any]:
        badges = await self.ensure_catalog(db)
        metric_values = await self._metric_values(db, user)

        user_badges = {
            row.badge_id: row
            for row in (
                await db.execute(
                    select(UserAchievementBadge).where(UserAchievementBadge.user_id == user.id)
                )
            ).scalars().all()
        }

        rows: List[Dict[str, Any]] = []
        for badge in badges:
            if not badge.is_active:
                continue

            current_value = float(metric_values.get(badge.metric, 0.0))
            target_value = max(float(badge.target_value or 0.0), 0.0)
            progress = 100.0 if target_value <= 0 else min(100.0, (current_value / target_value) * 100.0)
            unlocked = current_value >= target_value
            user_badge = user_badges.get(badge.id)

            if unlocked and user_badge is None:
                user_badge = UserAchievementBadge(
                    user_id=user.id,
                    badge_id=badge.id,
                    progress_value=current_value,
                )
                db.add(user_badge)
                user_badges[badge.id] = user_badge
                await db.flush()
            elif user_badge is not None and current_value > float(user_badge.progress_value or 0):
                user_badge.progress_value = current_value

            rows.append(
                {
                    "id": badge.id,
                    "code": badge.code,
                    "title": badge.title,
                    "description": badge.description,
                    "category": badge.category,
                    "metric": badge.metric,
                    "target_value": target_value,
                    "current_value": current_value,
                    "progress_percentage": round(progress, 1),
                    "is_unlocked": user_badge is not None,
                    "unlocked_at": user_badge.unlocked_at if user_badge else None,
                    "badge_icon": badge.badge_icon,
                    "badge_color": badge.badge_color,
                    "sort_order": badge.sort_order,
                }
            )

        rows.sort(key=lambda item: item["sort_order"])
        unlocked_rows = [item for item in rows if item["is_unlocked"]]
        locked_rows = [item for item in rows if not item["is_unlocked"]]
        next_milestones = sorted(
            locked_rows,
            key=lambda item: (-item["progress_percentage"], item["sort_order"]),
        )[:4]
        featured = sorted(
            unlocked_rows,
            key=lambda item: (item["unlocked_at"] or datetime.min),
            reverse=True,
        )[:4]

        total_count = len(rows)
        unlocked_count = len(unlocked_rows)
        return {
            "total_count": total_count,
            "unlocked_count": unlocked_count,
            "overall_progress": round((unlocked_count / total_count * 100.0), 1) if total_count else 0.0,
            "featured": featured,
            "next_milestones": next_milestones,
            "badges": rows,
        }


achievement_service = AchievementService()
