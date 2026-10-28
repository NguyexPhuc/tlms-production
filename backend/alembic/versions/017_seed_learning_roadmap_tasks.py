"""seed learning roadmap tasks

Revision ID: 017_seed_learning_roadmap_tasks
Revises: 016_daily_quest_limit_five
Create Date: 2026-09-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "017_seed_learning_roadmap_tasks"
down_revision: Union[str, None] = "016_daily_quest_limit_five"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROADMAP_TASKS = [
    {
        "id": "05a2846b-0c51-4e83-b62b-5c9f5f9e4c01",
        "title": "Làm quen Git và quy trình commit",
        "description": "Thực hành clone repository, tạo branch, commit nhỏ gọn và mở pull request theo quy trình lab.",
        "difficulty": "easy",
        "xp_reward": 50,
        "skill_tags": ["git", "github", "workflow"],
        "instructions": "Tạo một branch thực hành, chỉnh README nháp hoặc note cá nhân, commit với message rõ ràng và ghi lại các lệnh đã dùng.",
        "reference_links": ["https://docs.github.com/en/get-started"],
        "order_index": 10,
    },
    {
        "id": "e5653f8e-3346-4d3a-9a4c-b94338c39f7e",
        "title": "Chạy môi trường Docker Compose",
        "description": "Đọc docker-compose của TLMS, khởi động backend/frontend/database và kiểm tra logs cơ bản.",
        "difficulty": "easy",
        "xp_reward": 60,
        "skill_tags": ["docker", "compose", "devops"],
        "instructions": "Chạy docker compose up, kiểm tra trạng thái container, đọc logs backend/frontend và ghi lại lỗi nếu có.",
        "reference_links": ["https://docs.docker.com/compose/"],
        "order_index": 20,
    },
    {
        "id": "44ff4614-4d50-4a8c-a923-bfc7618e71ea",
        "title": "Khám phá FastAPI và Swagger",
        "description": "Mở Swagger, thử một endpoint đọc dữ liệu và ghi chú request/response quan trọng.",
        "difficulty": "medium",
        "xp_reward": 80,
        "skill_tags": ["fastapi", "api", "swagger"],
        "instructions": "Truy cập /docs, tìm endpoint phù hợp role hiện tại, thử request hợp lệ và chụp lại response mẫu.",
        "reference_links": ["https://fastapi.tiangolo.com/tutorial/"],
        "order_index": 30,
    },
    {
        "id": "d2d2bf1e-d6b9-43f1-a428-12e92f44c1df",
        "title": "Thực hành PostgreSQL và migration",
        "description": "Tìm hiểu bảng chính của TLMS, đọc migration Alembic và viết mô tả quan hệ dữ liệu.",
        "difficulty": "medium",
        "xp_reward": 90,
        "skill_tags": ["postgresql", "sqlalchemy", "alembic"],
        "instructions": "Xem các migration gần nhất, xác định ít nhất 3 bảng chính và giải thích khóa ngoại giữa chúng.",
        "reference_links": ["https://alembic.sqlalchemy.org/en/latest/"],
        "order_index": 40,
    },
    {
        "id": "64f108a0-6604-464d-92f5-2f95c749d0be",
        "title": "Cải thiện một màn hình Next.js nhỏ",
        "description": "Chọn một phần UI nhỏ, đọc component hiện có và đề xuất cải thiện trải nghiệm người dùng.",
        "difficulty": "hard",
        "xp_reward": 110,
        "skill_tags": ["nextjs", "typescript", "tailwind", "frontend"],
        "instructions": "Đọc một page trong frontend/src/app, ghi lại state/API đang dùng và đề xuất một cải tiến có thể kiểm thử.",
        "reference_links": ["https://nextjs.org/docs/app"],
        "order_index": 50,
    },
]


def upgrade() -> None:
    op.execute(
        """
        UPDATE tasks
        SET is_active = false, updated_at = now()
        WHERE title LIKE 'TLMS Daily Smoke%'
        """
    )

    for task in ROADMAP_TASKS:
        op.execute(
            f"""
            INSERT INTO tasks (
                id,
                title,
                description,
                type,
                scope,
                difficulty,
                min_level_required,
                max_participants,
                assignee_ids,
                prerequisite_task_ids,
                xp_reward,
                skill_tags,
                instructions,
                reference_links,
                is_active,
                order_index,
                creator_id,
                creator_type,
                target_member_level,
                requires_manager_review,
                created_at,
                updated_at
            )
            SELECT
                '{task["id"]}'::uuid,
                '{task["title"].replace("'", "''")}',
                '{task["description"].replace("'", "''")}',
                'core'::tasktype,
                'mandatory'::taskscope,
                '{task["difficulty"]}'::taskdifficulty,
                1,
                NULL,
                ARRAY[]::varchar[],
                ARRAY[]::varchar[],
                {task["xp_reward"]},
                ARRAY[{", ".join(repr(tag) for tag in task["skill_tags"])}]::varchar[],
                '{task["instructions"].replace("'", "''")}',
                ARRAY[{", ".join(repr(link) for link in task["reference_links"])}]::varchar[],
                true,
                {task["order_index"]},
                (SELECT id FROM users WHERE roles @> ARRAY['admin']::varchar[] ORDER BY created_at LIMIT 1),
                'system'::taskcreatortype,
                'new'::memberlevel,
                true,
                now(),
                now()
            WHERE NOT EXISTS (
                SELECT 1 FROM tasks WHERE title = '{task["title"].replace("'", "''")}'
            )
            """
        )


def downgrade() -> None:
    ids = ", ".join(f"'{task['id']}'::uuid" for task in ROADMAP_TASKS)
    op.execute(f"DELETE FROM tasks WHERE id IN ({ids})")
    op.execute(
        """
        UPDATE tasks
        SET is_active = true, updated_at = now()
        WHERE title LIKE 'TLMS Daily Smoke%'
        """
    )
