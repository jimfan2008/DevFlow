"""initial migration

Revision ID: 001
Revises:
Create Date: 2026-04-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------
    # 1. users — 用户表 (无外键依赖)
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100)),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("last_login_at", sa.DateTime()),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.Index("idx_users_email", "email"),
        sa.Index("idx_users_username", "username"),
    )

    # ------------------------------------------------------------------
    # 2. projects — 项目表
    # ------------------------------------------------------------------
    op.create_table(
        "projects",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("creator_id", sa.String(),
                   sa.ForeignKey("users.id"), nullable=True),
        sa.Column("max_tasks", sa.Integer(), server_default="1000"),
        sa.Column("is_public", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime()),
        sa.UniqueConstraint("slug", name="uq_projects_slug"),
    )

    # ------------------------------------------------------------------
    # 3. project_members — 项目成员表
    # ------------------------------------------------------------------
    op.create_table(
        "project_members",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(),
                   sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(),
                   sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), server_default="member"),
        sa.Column("joined_at", sa.DateTime(),
                   server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("project_id", "user_id",
                            name="uq_project_members_project_user"),
        sa.Index("idx_project_members_project", "project_id"),
        sa.Index("idx_project_members_user", "user_id"),
    )

    # ------------------------------------------------------------------
    # 4. boards — 看板表
    # ------------------------------------------------------------------
    op.create_table(
        "boards",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(),
                   sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("position", sa.Integer(), server_default="0"),
        sa.Column("color", sa.String(7), server_default="#3B82F6"),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Index("idx_boards_project", "project_id"),
        sa.UniqueConstraint("project_id", "slug",
                            name="uq_board_project_slug"),
    )

    # ------------------------------------------------------------------
    # 5. board_columns — 看板列/泳道表
    # ------------------------------------------------------------------
    op.create_table(
        "board_columns",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("board_id", sa.String(),
                   sa.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("color", sa.String(7), server_default="#E5E7EB"),
        sa.Column("position", sa.Integer(), server_default="0"),
        sa.Column("max_tasks", sa.Integer()),
        sa.Column("is_swimlane", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Index("idx_board_columns_board", "board_id"),
        sa.UniqueConstraint("board_id", "slug",
                            name="uq_board_column_board_slug"),
    )

    # ------------------------------------------------------------------
    # 6. tasks — 任务表
    # ------------------------------------------------------------------
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("board_id", sa.String(),
                   sa.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("column_id", sa.String(),
                   sa.ForeignKey("board_columns.id", ondelete="RESTRICT")),
        sa.Column("status", sa.String(50), server_default="todo"),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("is_blocked", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("blocked_by_count", sa.Integer(), server_default="0"),
        sa.Column("assignee_id", sa.String(),
                   sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("creator_id", sa.String(),
                   sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False),
        sa.Column("watcher_ids", sa.Text(), server_default="[]"),
        sa.Column("due_date", sa.DateTime()),
        sa.Column("estimated_hours", sa.Float()),
        sa.Column("actual_hours", sa.Float()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("order_in_column", sa.Integer(), server_default="0"),
        sa.Column("is_visible", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Index("idx_tasks_board", "board_id"),
        sa.Index("idx_tasks_column", "column_id"),
        sa.Index("idx_tasks_status", "status"),
        sa.Index("idx_tasks_assignee", "assignee_id"),
        sa.Index("idx_tasks_creator", "creator_id"),
        sa.Index("idx_tasks_due_date", "due_date"),
        sa.Index("idx_tasks_is_blocked", "is_blocked",
                   sqlite_where=Column("is_blocked").is_(True)),
    )

    # ------------------------------------------------------------------
    # 7. task_dependencies — 任务依赖表
    # ------------------------------------------------------------------
    op.create_table(
        "task_dependencies",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("source_task_id", sa.String(),
                   sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_task_id", sa.String(),
                   sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dependency_type", sa.String(20),
                   server_default="finishes_to_starts"),
        sa.Column("created_at", sa.DateTime(),
                   server_default=sa.func.current_timestamp()),
        sa.Index("idx_task_deps_source", "source_task_id"),
        sa.Index("idx_task_deps_target", "target_task_id"),
    )

    # ------------------------------------------------------------------
    # 8. comments — 评论表
    # ------------------------------------------------------------------
    op.create_table(
        "comments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("task_id", sa.String(),
                   sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(),
                   sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Index("idx_comments_task", "task_id"),
        sa.Index("idx_comments_user", "user_id"),
    )

    # ------------------------------------------------------------------
    # 9. attachments — 附件表
    # ------------------------------------------------------------------
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("task_id", sa.String(),
                   sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_url", sa.String(1000)),
        sa.Column("size", sa.Integer(), server_default="0"),
        sa.Column("type", sa.String(100),
                   server_default="application/octet-stream"),
        sa.Column("uploaded_by", sa.String(),
                   sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Index("idx_attachments_task", "task_id"),
        sa.Index("idx_attachments_uploaded_by", "uploaded_by"),
    )

    # ------------------------------------------------------------------
    # 10. inbox_items — 收件箱表
    # ------------------------------------------------------------------
    op.create_table(
        "inbox_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(),
                   sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.String(),
                   sa.ForeignKey("tasks.id", ondelete="CASCADE")),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), server_default=""),
        sa.Column("content", sa.Text(), server_default=""),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("metadata_json", sa.Text(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(),
                   server_default=sa.func.current_timestamp()),
        sa.Index("idx_inbox_user", "user_id"),
        sa.Index("idx_inbox_user_unread", "user_id", "is_read"),
        sa.Index("idx_inbox_task", "task_id"),
        sa.Index("idx_inbox_type", "type"),
    )

    # ------------------------------------------------------------------
    # 11. notifications — 通知偏好设置表
    # ------------------------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(),
                   sa.ForeignKey("users.id", ondelete="CASCADE"),
                   nullable=False, unique=True),
        sa.Column("frequency", sa.String(20), server_default="realtime"),
        sa.Column("notify_types", sa.Text(), server_default="[]"),
        sa.Column("suppress_watch", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(),
                   server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Index("idx_notifications_user", "user_id"),
    )


def downgrade():
    """按依赖关系的逆序逐表删除。"""
    op.drop_table("notifications")
    op.drop_table("inbox_items")
    op.drop_table("attachments")
    op.drop_table("comments")
    op.drop_table("task_dependencies")
    op.drop_table("tasks")
    op.drop_table("board_columns")
    op.drop_table("boards")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("users")
