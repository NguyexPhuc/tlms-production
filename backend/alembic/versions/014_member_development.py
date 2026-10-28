"""member development workflow

Revision ID: 014_member_development
Revises: 013_add_evening_shift
Create Date: 2026-08-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "014_member_development"
down_revision: Union[str, None] = "013_add_evening_shift"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    memberlevel = postgresql.ENUM("new", "diligent", "official", name="memberlevel")
    memberlevel.create(bind, checkfirst=True)

    taskcreatortype = postgresql.ENUM("ai", "manager", "system", name="taskcreatortype")
    taskcreatortype.create(bind, checkfirst=True)

    dailytaskstatus = postgresql.ENUM("complete", "partial", "missed", name="dailytaskstatus")
    dailytaskstatus.create(bind, checkfirst=True)

    questionstatus = postgresql.ENUM("active", "archived", name="questionstatus")
    questionstatus.create(bind, checkfirst=True)

    questionanswerstatus = postgresql.ENUM(
        "not_started",
        "submitted",
        "ai_reviewed",
        "approved",
        "rejected",
        name="questionanswerstatus",
    )
    questionanswerstatus.create(bind, checkfirst=True)

    promotionstatus = postgresql.ENUM("eligible", "pending", "approved", "rejected", name="promotionstatus")
    promotionstatus.create(bind, checkfirst=True)

    notificationchannel = postgresql.ENUM("in_app", "email", "push", "sms", name="notificationchannel")
    notificationchannel.create(bind, checkfirst=True)

    op.execute("ALTER TYPE taskdifficulty ADD VALUE IF NOT EXISTS 'advanced'")
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'ai_reviewed'")
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'late'")
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'missed'")

    op.add_column("users", sa.Column("reliability_score", sa.Float(), nullable=False, server_default="100"))
    op.add_column("users", sa.Column("member_score", sa.Float(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("promotion_progress", sa.Float(), nullable=False, server_default="0"))
    op.add_column(
        "users",
        sa.Column(
            "member_level",
            postgresql.ENUM("new", "diligent", "official", name="memberlevel", create_type=False),
            nullable=False,
            server_default="new",
        ),
    )

    op.execute(
        """
        UPDATE users
        SET member_level = CASE
            WHEN roles @> ARRAY['admin']::varchar[] THEN 'official'::memberlevel
            WHEN roles @> ARRAY['mentor']::varchar[] THEN 'official'::memberlevel
            WHEN roles @> ARRAY['member']::varchar[] THEN 'official'::memberlevel
            ELSE 'new'::memberlevel
        END
        """
    )

    op.add_column("tasks", sa.Column("deadline", sa.DateTime(), nullable=True))
    op.add_column("tasks", sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True))
    op.add_column(
        "tasks",
        sa.Column(
            "creator_type",
            postgresql.ENUM("ai", "manager", "system", name="taskcreatortype", create_type=False),
            nullable=False,
            server_default="manager",
        ),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "target_member_level",
            postgresql.ENUM("new", "diligent", "official", name="memberlevel", create_type=False),
            nullable=False,
            server_default="new",
        ),
    )
    op.add_column("tasks", sa.Column("requires_manager_review", sa.Boolean(), nullable=False, server_default="true"))

    op.add_column("user_tasks", sa.Column("assigned_for_date", sa.Date(), nullable=True))
    op.add_column("user_tasks", sa.Column("deadline_at", sa.DateTime(), nullable=True))
    op.add_column("user_tasks", sa.Column("progress_percentage", sa.Float(), nullable=False, server_default="0"))
    op.add_column("user_tasks", sa.Column("completion_percentage", sa.Float(), nullable=False, server_default="0"))
    op.add_column(
        "user_tasks",
        sa.Column("evidence_links", postgresql.ARRAY(sa.String(length=500)), nullable=False, server_default="{}"),
    )
    op.add_column("user_tasks", sa.Column("ai_score", sa.Float(), nullable=True))
    op.add_column("user_tasks", sa.Column("ai_feedback", sa.Text(), nullable=True))
    op.add_column("user_tasks", sa.Column("manager_score", sa.Float(), nullable=True))
    op.add_column("user_tasks", sa.Column("final_score", sa.Float(), nullable=True))
    op.add_column("user_tasks", sa.Column("final_feedback", sa.Text(), nullable=True))
    op.add_column("user_tasks", sa.Column("needs_manager_review", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("user_tasks", sa.Column("assigned_by_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_user_tasks_assigned_by_id_users",
        "user_tasks",
        "users",
        ["assigned_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_index("ix_user_tasks_user_task", table_name="user_tasks")
    op.create_index(
        "ix_user_tasks_user_task_unassigned",
        "user_tasks",
        ["user_id", "task_id"],
        unique=True,
        postgresql_where=sa.text("assigned_for_date IS NULL"),
    )
    op.create_index(
        "ix_user_tasks_user_task_day",
        "user_tasks",
        ["user_id", "task_id", "assigned_for_date"],
        unique=True,
        postgresql_where=sa.text("assigned_for_date IS NOT NULL"),
    )
    op.create_index("ix_user_tasks_assigned_for_date", "user_tasks", ["assigned_for_date"])
    op.create_index("ix_user_tasks_deadline_at", "user_tasks", ["deadline_at"])
    op.create_index("ix_user_tasks_assigned_by_id", "user_tasks", ["assigned_by_id"])

    op.create_table(
        "task_progress_updates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("progress_percentage", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_task_id"], ["user_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_task_progress_updates_user_task_id", "task_progress_updates", ["user_task_id"])
    op.create_index("ix_task_progress_updates_user_id", "task_progress_updates", ["user_id"])

    op.create_table(
        "daily_task_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("assigned_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("late_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("missed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "attendance_status",
            postgresql.ENUM("complete", "partial", "missed", name="dailytaskstatus", create_type=False),
            nullable=False,
            server_default="missed",
        ),
        sa.Column("discipline_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reliability_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("generated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("recalculated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "report_date", name="uq_daily_task_reports_user_date"),
    )
    op.create_index("ix_daily_task_reports_user_id", "daily_task_reports", ["user_id"])
    op.create_index("ix_daily_task_reports_report_date", "daily_task_reports", ["report_date"])

    op.create_table(
        "questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "difficulty",
            postgresql.ENUM(
                "easy",
                "medium",
                "hard",
                "expert",
                "advanced",
                name="taskdifficulty",
                create_type=False,
            ),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expected_duration_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "target_member_level",
            postgresql.ENUM("new", "diligent", "official", name="memberlevel", create_type=False),
            nullable=False,
            server_default="new",
        ),
        sa.Column(
            "creator_type",
            postgresql.ENUM("ai", "manager", "system", name="taskcreatortype", create_type=False),
            nullable=False,
            server_default="manager",
        ),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expected_answer", sa.Text(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("active", "archived", name="questionstatus", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_questions_target_member_level", "questions", ["target_member_level"])
    op.create_index("ix_questions_status", "questions", ["status"])

    op.create_table(
        "user_question_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("ai_score", sa.Float(), nullable=True),
        sa.Column("ai_feedback", sa.Text(), nullable=True),
        sa.Column("manager_score", sa.Float(), nullable=True),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "not_started",
                "submitted",
                "ai_reviewed",
                "approved",
                "rejected",
                name="questionanswerstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="submitted",
        ),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "question_id", name="uq_user_question_answers_user_question"),
    )
    op.create_index("ix_user_question_answers_user_id", "user_question_answers", ["user_id"])
    op.create_index("ix_user_question_answers_status", "user_question_answers", ["status"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "channel",
            postgresql.ENUM("in_app", "email", "push", "sms", name="notificationchannel", create_type=False),
            nullable=False,
            server_default="in_app",
        ),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_read_at", "notifications", ["read_at"])

    op.create_table(
        "promotion_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "from_member_level",
            postgresql.ENUM("new", "diligent", "official", name="memberlevel", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "to_member_level",
            postgresql.ENUM("new", "diligent", "official", name="memberlevel", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM("eligible", "pending", "approved", "rejected", name="promotionstatus", create_type=False),
            nullable=False,
            server_default="eligible",
        ),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("manager_notes", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_promotion_reviews_user_id", "promotion_reviews", ["user_id"])
    op.create_index("ix_promotion_reviews_status", "promotion_reviews", ["status"])

    op.create_table(
        "member_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_completion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("task_quality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("attendance_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("discipline_score", sa.Float(), nullable=False, server_default="100"),
        sa.Column("activity_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("manager_score", sa.Float(), nullable=True),
        sa.Column("final_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_member_evaluations_user_id", "member_evaluations", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_member_evaluations_user_id", table_name="member_evaluations")
    op.drop_table("member_evaluations")

    op.drop_index("ix_promotion_reviews_status", table_name="promotion_reviews")
    op.drop_index("ix_promotion_reviews_user_id", table_name="promotion_reviews")
    op.drop_table("promotion_reviews")

    op.drop_index("ix_notifications_read_at", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_user_question_answers_status", table_name="user_question_answers")
    op.drop_index("ix_user_question_answers_user_id", table_name="user_question_answers")
    op.drop_table("user_question_answers")

    op.drop_index("ix_questions_status", table_name="questions")
    op.drop_index("ix_questions_target_member_level", table_name="questions")
    op.drop_table("questions")

    op.drop_index("ix_daily_task_reports_report_date", table_name="daily_task_reports")
    op.drop_index("ix_daily_task_reports_user_id", table_name="daily_task_reports")
    op.drop_table("daily_task_reports")

    op.drop_index("ix_task_progress_updates_user_id", table_name="task_progress_updates")
    op.drop_index("ix_task_progress_updates_user_task_id", table_name="task_progress_updates")
    op.drop_table("task_progress_updates")

    op.drop_index("ix_user_tasks_assigned_by_id", table_name="user_tasks")
    op.drop_index("ix_user_tasks_deadline_at", table_name="user_tasks")
    op.drop_index("ix_user_tasks_assigned_for_date", table_name="user_tasks")
    op.drop_index("ix_user_tasks_user_task_day", table_name="user_tasks")
    op.drop_index("ix_user_tasks_user_task_unassigned", table_name="user_tasks")
    op.create_index("ix_user_tasks_user_task", "user_tasks", ["user_id", "task_id"], unique=True)
    op.drop_constraint("fk_user_tasks_assigned_by_id_users", "user_tasks", type_="foreignkey")
    op.drop_column("user_tasks", "assigned_by_id")
    op.drop_column("user_tasks", "needs_manager_review")
    op.drop_column("user_tasks", "final_feedback")
    op.drop_column("user_tasks", "final_score")
    op.drop_column("user_tasks", "manager_score")
    op.drop_column("user_tasks", "ai_feedback")
    op.drop_column("user_tasks", "ai_score")
    op.drop_column("user_tasks", "evidence_links")
    op.drop_column("user_tasks", "completion_percentage")
    op.drop_column("user_tasks", "progress_percentage")
    op.drop_column("user_tasks", "deadline_at")
    op.drop_column("user_tasks", "assigned_for_date")

    op.drop_column("tasks", "requires_manager_review")
    op.drop_column("tasks", "target_member_level")
    op.drop_column("tasks", "creator_type")
    op.drop_column("tasks", "estimated_duration_minutes")
    op.drop_column("tasks", "deadline")

    op.drop_column("users", "member_level")
    op.drop_column("users", "promotion_progress")
    op.drop_column("users", "member_score")
    op.drop_column("users", "reliability_score")

    op.execute("DROP TYPE IF EXISTS notificationchannel")
    op.execute("DROP TYPE IF EXISTS promotionstatus")
    op.execute("DROP TYPE IF EXISTS questionanswerstatus")
    op.execute("DROP TYPE IF EXISTS questionstatus")
    op.execute("DROP TYPE IF EXISTS dailytaskstatus")
    op.execute("DROP TYPE IF EXISTS taskcreatortype")
    op.execute("DROP TYPE IF EXISTS memberlevel")
