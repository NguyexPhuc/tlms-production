"""add Zalo Daily Task Quiz integration

Revision ID: 024_zalo_daily_quiz
Revises: 023_weekly_cup_quiz
Create Date: 2026-10-15 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "024_zalo_daily_quiz"
down_revision: Union[str, None] = "023_weekly_cup_quiz"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("options", sa.JSON(), nullable=True))
    op.add_column("questions", sa.Column("correct_option", sa.String(length=1), nullable=True))

    zalo_provider = postgresql.ENUM("mock", "zalo_oa", name="zaloprovider", create_type=False)
    zalo_link_status = postgresql.ENUM("pending", "linked", "revoked", name="zalolinkstatus", create_type=False)
    zalo_quiz_status = postgresql.ENUM("active", "completed", "expired", name="zaloquizstatus", create_type=False)
    zalo_delivery_status = postgresql.ENUM("pending", "sent", "failed", "skipped", name="zalodeliverystatus", create_type=False)
    zalo_provider.create(op.get_bind(), checkfirst=True)
    zalo_link_status.create(op.get_bind(), checkfirst=True)
    zalo_quiz_status.create(op.get_bind(), checkfirst=True)
    zalo_delivery_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "zalo_integration_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("provider", zalo_provider, nullable=False, server_default="mock"),
        sa.Column("send_hour", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("send_minute", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reminder_hour", sa.Integer(), nullable=False, server_default="18"),
        sa.Column("reminder_minute", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quiz_size", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("session_ttl_minutes", sa.Integer(), nullable=False, server_default="720"),
        sa.Column("send_window_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "zalo_user_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("zalo_user_id", sa.String(length=100), nullable=True),
        sa.Column("status", zalo_link_status, nullable=False, server_default="pending"),
        sa.Column("consent_granted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("link_token_hash", sa.String(length=64), nullable=True),
        sa.Column("link_expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_interaction_at", sa.DateTime(), nullable=True),
        sa.Column("linked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_zalo_user_links_user_id"),
        sa.UniqueConstraint("zalo_user_id", name="uq_zalo_user_links_zalo_user_id"),
        sa.UniqueConstraint("link_token_hash", name="uq_zalo_user_links_link_token_hash"),
    )
    op.create_index("ix_zalo_user_links_zalo_user_id", "zalo_user_links", ["zalo_user_id"])

    op.create_table(
        "zalo_quiz_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("status", zalo_quiz_status, nullable=False, server_default="active"),
        sa.Column("total_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_position", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("answered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attendance_applied", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "session_date", name="uq_zalo_quiz_sessions_user_date"),
    )
    op.create_index("ix_zalo_quiz_sessions_date_status", "zalo_quiz_sessions", ["session_date", "status"])

    op.create_table(
        "zalo_quiz_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("correct_option", sa.String(length=1), nullable=False),
        sa.Column("selected_option", sa.String(length=1), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("points_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("answered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["session_id"], ["zalo_quiz_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("session_id", "position", name="uq_zalo_quiz_items_session_position"),
        sa.UniqueConstraint("session_id", "question_id", name="uq_zalo_quiz_items_session_question"),
    )

    op.create_table(
        "zalo_notification_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("link_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("idempotency_key", sa.String(length=180), nullable=False),
        sa.Column("status", zalo_delivery_status, nullable=False, server_default="pending"),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column("external_message_id", sa.String(length=150), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["link_id"], ["zalo_user_links.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["zalo_quiz_sessions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("idempotency_key", name="uq_zalo_notification_logs_idempotency_key"),
    )
    op.create_index("ix_zalo_notification_logs_status_retry", "zalo_notification_logs", ["status", "next_retry_at"])

    op.create_table(
        "zalo_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_key", sa.String(length=150), nullable=False),
        sa.Column("event_name", sa.String(length=80), nullable=False),
        sa.Column("sender_hash", sa.String(length=64), nullable=True),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("signature_valid", sa.Boolean(), nullable=False),
        sa.Column("processing_status", sa.String(length=30), nullable=False, server_default="received"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("event_key", name="uq_zalo_webhook_events_event_key"),
    )


def downgrade() -> None:
    op.drop_table("zalo_webhook_events")
    op.drop_index("ix_zalo_notification_logs_status_retry", table_name="zalo_notification_logs")
    op.drop_table("zalo_notification_logs")
    op.drop_table("zalo_quiz_items")
    op.drop_index("ix_zalo_quiz_sessions_date_status", table_name="zalo_quiz_sessions")
    op.drop_table("zalo_quiz_sessions")
    op.drop_index("ix_zalo_user_links_zalo_user_id", table_name="zalo_user_links")
    op.drop_table("zalo_user_links")
    op.drop_table("zalo_integration_configs")

    sa.Enum(name="zalodeliverystatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="zaloquizstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="zalolinkstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="zaloprovider").drop(op.get_bind(), checkfirst=True)

    op.drop_column("questions", "correct_option")
    op.drop_column("questions", "options")
