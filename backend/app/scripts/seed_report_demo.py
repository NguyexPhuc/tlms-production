"""Prepare deterministic learner progress for a TLMS report/demo.

The script is idempotent for a given Vietnam calendar date. It only updates
candidate/member accounts; management accounts are intentionally excluded.
"""
import argparse
import asyncio
from datetime import date, datetime, time, timedelta

import pytz
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.development import DailyTaskReport, DailyTaskStatus
from app.models.quest import (
    DailyQuest,
    DailyQuestDifficulty,
    DailyQuestStatus,
    DailyQuestType,
)
from app.models.task import (
    Task,
    TaskCreatorType,
    TaskDifficulty,
    TaskScope,
    TaskStatus,
    TaskType,
    UserTask,
)
from app.models.user import MemberLevel, User, UserRole, UserStatus


VN_TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")
QUEST_LIMIT = 5

QUEST_TEMPLATES = (
    (
        "API: xử lý hai người đặt cùng một ghế",
        "Mô tả cách backend dùng transaction và ràng buộc duy nhất để chỉ một yêu cầu đặt ghế thành công.",
        DailyQuestDifficulty.MEDIUM,
        20,
    ),
    (
        "SQL: chọn người dùng chưa có nhiệm vụ",
        "Viết truy vấn LEFT JOIN để lấy tất cả người dùng chưa có bản ghi tương ứng trong bảng nhiệm vụ.",
        DailyQuestDifficulty.EASY,
        10,
    ),
    (
        "Frontend: ngăn người dùng gửi form hai lần",
        "Trình bày loading state, khóa nút gửi và cách xử lý lỗi để tránh tạo dữ liệu trùng.",
        DailyQuestDifficulty.EASY,
        10,
    ),
    (
        "Docker: kiểm tra service không kết nối được database",
        "Nêu các bước đọc log, kiểm tra biến môi trường, network và healthcheck khi backend mất kết nối PostgreSQL.",
        DailyQuestDifficulty.MEDIUM,
        20,
    ),
    (
        "Logic code: tìm phần tử xuất hiện đầu tiên hai lần",
        "Viết hàm nhận một mảng số và trả về phần tử đầu tiên bị lặp; nêu độ phức tạp thời gian và bộ nhớ.",
        DailyQuestDifficulty.HARD,
        35,
    ),
)

DAILY_TASK_TEMPLATES = (
    ("Daily Demo: kiểm tra API", "Gọi một endpoint và ghi lại status code cùng kết quả nhận được."),
    ("Daily Demo: truy vấn SQL", "Viết và kiểm tra một truy vấn JOIN ngắn trên dữ liệu mẫu."),
    ("Daily Demo: rà soát giao diện", "Kiểm tra một luồng giao diện trên desktop và mobile, sau đó ghi nhận kết quả."),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Demo date in YYYY-MM-DD; defaults to today in Vietnam")
    parser.add_argument("--dry-run", action="store_true", help="Rollback after preparing and printing the summary")
    return parser.parse_args()


def resolve_date(raw_value: str | None) -> date:
    if raw_value:
        return date.fromisoformat(raw_value)
    return datetime.now(VN_TIMEZONE).date()


def learner_xp(index: int, current_xp: int) -> int:
    """Return stable, varied XP without removing progress already earned."""
    return max(current_xp, 95 + index * 37)


async def ensure_daily_task_templates(db) -> list[Task]:
    templates: list[Task] = []
    for order_index, (title, description) in enumerate(DAILY_TASK_TEMPLATES, start=900):
        task = (
            await db.execute(select(Task).where(Task.title == title))
        ).scalar_one_or_none()
        if task is None:
            task = Task(
                title=title,
                description=description,
                type=TaskType.CORE,
                scope=TaskScope.PRIVATE,
                difficulty=TaskDifficulty.EASY,
                min_level_required=1,
                xp_reward=0,
                skill_tags=["demo", "daily-task"],
                instructions=description,
                creator_type=TaskCreatorType.SYSTEM,
                target_member_level=MemberLevel.NEW,
                requires_manager_review=False,
                estimated_duration_minutes=15,
                is_active=True,
                order_index=order_index,
            )
            db.add(task)
            await db.flush()
        templates.append(task)
    return templates


async def ensure_quests(db, user: User, index: int, target_date: date) -> tuple[int, int]:
    window_start = datetime.combine(target_date, time.min)
    window_end = window_start + timedelta(days=1)
    quests = list(
        (
            await db.execute(
                select(DailyQuest)
                .where(
                    DailyQuest.user_id == user.id,
                    DailyQuest.quest_type == DailyQuestType.DAILY,
                    DailyQuest.created_at >= window_start,
                    DailyQuest.created_at < window_end,
                )
                .order_by(DailyQuest.created_at, DailyQuest.id)
            )
        ).scalars().all()
    )

    for position in range(len(quests), QUEST_LIMIT):
        title, description, difficulty, reward = QUEST_TEMPLATES[position]
        quest = DailyQuest(
            user_id=user.id,
            title=title,
            description=description,
            quest_type=DailyQuestType.DAILY,
            difficulty=difficulty,
            xp_reward=reward,
            status=DailyQuestStatus.PENDING,
            created_at=window_start + timedelta(hours=7, minutes=position * 5),
            expires_at=window_end,
            auto_pass_score=70,
        )
        db.add(quest)
        quests.append(quest)

    completed_target = 1 + index % QUEST_LIMIT
    for position, quest in enumerate(quests[:completed_target]):
        if quest.status != DailyQuestStatus.COMPLETED:
            quest.status = DailyQuestStatus.COMPLETED
            quest.completed_at = window_start + timedelta(hours=9, minutes=index * 3 + position)
            quest.submitted_at = quest.completed_at - timedelta(minutes=8)
            quest.reviewed_at = quest.completed_at
            quest.proof_text = "Đã hoàn thành nội dung thực hành và kiểm tra kết quả theo yêu cầu Daily Quest."
            quest.ai_score = float(76 + (index + position) % 20)
            quest.ai_feedback = "Bài làm đạt yêu cầu demo: đúng trọng tâm, có kết quả và giải thích ngắn gọn."

    completed_count = sum(quest.status == DailyQuestStatus.COMPLETED for quest in quests)
    return len(quests), completed_count


async def ensure_today_tasks(
    db,
    user: User,
    index: int,
    target_date: date,
    templates: list[Task],
) -> tuple[int, int]:
    completed_at = datetime.combine(target_date, time(hour=10)) + timedelta(minutes=index * 4)
    task_count = 1 + index % len(templates)

    for task in templates[:task_count]:
        user_task = (
            await db.execute(
                select(UserTask).where(
                    UserTask.user_id == user.id,
                    UserTask.task_id == task.id,
                    UserTask.assigned_for_date == target_date,
                )
            )
        ).scalar_one_or_none()
        if user_task is None:
            user_task = UserTask(
                user_id=user.id,
                task_id=task.id,
                assigned_for_date=target_date,
                created_at=datetime.combine(target_date, time(hour=7, minute=30)),
            )
            db.add(user_task)

        user_task.status = TaskStatus.COMPLETED
        user_task.progress_percentage = 100.0
        user_task.completion_percentage = 100.0
        user_task.started_at = completed_at - timedelta(minutes=15)
        user_task.submitted_at = completed_at - timedelta(minutes=2)
        user_task.completed_at = completed_at
        user_task.reviewed_at = completed_at
        user_task.ai_score = float(78 + index % 18)
        user_task.final_score = user_task.ai_score
        user_task.ai_feedback = "Hoàn thành đúng yêu cầu Daily Task trong ngày."
        user_task.final_feedback = user_task.ai_feedback
        user_task.submission_notes = "Dữ liệu tiến độ dùng cho buổi báo cáo TLMS."
        user_task.needs_manager_review = False
        user_task.xp_earned = 0

    await db.flush()
    today_tasks = list(
        (
            await db.execute(
                select(UserTask).where(
                    UserTask.user_id == user.id,
                    UserTask.assigned_for_date == target_date,
                )
            )
        ).scalars().all()
    )
    completed_count = sum(
        task.status in (TaskStatus.COMPLETED, TaskStatus.APPROVED) for task in today_tasks
    )
    assigned_count = len(today_tasks)
    completion_rate = round(completed_count / assigned_count * 100.0, 1) if assigned_count else 0.0

    report = (
        await db.execute(
            select(DailyTaskReport).where(
                DailyTaskReport.user_id == user.id,
                DailyTaskReport.report_date == target_date,
            )
        )
    ).scalar_one_or_none()
    if report is None:
        report = DailyTaskReport(user_id=user.id, report_date=target_date)
        db.add(report)
    report.assigned_count = assigned_count
    report.completed_count = completed_count
    report.late_count = 0
    report.missed_count = max(0, assigned_count - completed_count)
    report.completion_rate = completion_rate
    report.attendance_status = (
        DailyTaskStatus.COMPLETE
        if assigned_count and completed_count == assigned_count
        else DailyTaskStatus.PARTIAL
        if completed_count
        else DailyTaskStatus.MISSED
    )
    report.discipline_delta = 0.0
    report.reliability_delta = 0.0
    report.recalculated_at = datetime.utcnow()
    return assigned_count, completed_count


async def seed(target_date: date, dry_run: bool) -> None:
    async with AsyncSessionLocal() as db:
        learners = list(
            (
                await db.execute(
                    select(User)
                    .where(
                        User.status == UserStatus.ACTIVE,
                        User.roles.overlap([UserRole.CANDIDATE.value, UserRole.MEMBER.value]),
                    )
                    .order_by(User.created_at, User.id)
                )
            ).scalars().all()
        )
        management_count = (
            len((await db.execute(select(User.id))).scalars().all()) - len(learners)
        )
        task_templates = await ensure_daily_task_templates(db)

        print(
            f"Preparing report data for {target_date.isoformat()}: "
            f"{len(learners)} learners, {management_count} management accounts skipped"
        )
        for index, user in enumerate(learners):
            user.current_xp = learner_xp(index, user.current_xp or 0)
            user.level = user.calculate_level()
            quest_total, quest_completed = await ensure_quests(db, user, index, target_date)
            task_total, task_completed = await ensure_today_tasks(
                db, user, index, target_date, task_templates
            )
            print(
                f"{user.email}: level={user.level}, xp={user.current_xp}, "
                f"daily_quests={quest_completed}/{quest_total}, daily_tasks={task_completed}/{task_total}"
            )

        if dry_run:
            await db.rollback()
            print("Dry run complete; all changes rolled back")
        else:
            await db.commit()
            print(f"Report demo data committed for {len(learners)} learner accounts")


async def main() -> None:
    args = parse_args()
    await seed(resolve_date(args.date), args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
