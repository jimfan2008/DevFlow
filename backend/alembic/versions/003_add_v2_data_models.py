"""add v2 data models per design.md

Revision ID: 003
Revises: 002
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def _column_exists(table, column):
    conn = op.get_context().bind
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"
        ),
        {"t": table, "c": column},
    )
    return result.fetchone() is not None


def _table_exists(table):
    conn = op.get_context().bind
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name=:t AND table_schema='public'"
        ),
        {"t": table},
    )
    return result.fetchone() is not None


def _constraint_exists(name):
    conn = op.get_context().bind
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_constraint WHERE conname=:n"
        ),
        {"n": name},
    )
    return result.fetchone() is not None


def _index_exists(name):
    conn = op.get_context().bind
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname=:n"
        ),
        {"n": name},
    )
    return result.fetchone() is not None


def _add_column(table, column_obj):
    if not _column_exists(table, column_obj.name):
        op.add_column(table, column_obj)


def _add_check_constraint(table, name, check_clause):
    if not _constraint_exists(name):
        op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({check_clause})")


def _create_index(name, table, columns, **kw):
    if not _index_exists(name):
        op.create_index(name, table, columns, **kw)


def _ensure_table(name, *args, **kw):
    if not _table_exists(name):
        columns = args[0] if len(args) == 1 and isinstance(args[0], list) else args
        op.create_table(name, *columns, **kw)


def upgrade():
    _ensure_table(
        "groups",
        [
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text()),
            sa.Column("members", JSONB, server_default="[]"),
            sa.Column("host_agent", sa.String(100)),
            sa.Column("mode", sa.String(20), server_default="discussion"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        ],
    )

    _ensure_table(
        "group_messages",
        [
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("group_id", sa.String(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sender", sa.String(100), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
            sa.Column("is_streaming", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("msg_metadata", JSONB, server_default="{}"),
        ],
    )

    _ensure_table(
        "meeting_outcomes",
        [
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("group_id", sa.String(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("meeting_topic", sa.String(500), nullable=False),
            sa.Column("host_agent", sa.String(100), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ended_at", sa.DateTime(timezone=True)),
            sa.Column("minutes", sa.Text()),
            sa.Column("decisions", JSONB, server_default="[]"),
            sa.Column("todos", JSONB, server_default="[]"),
            sa.Column("risks", JSONB, server_default="[]"),
            sa.Column("open_issues", JSONB, server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        ],
    )

    _ensure_table(
        "group_tasks",
        [
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("group_id", sa.String(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("meeting_id", sa.String(), sa.ForeignKey("meeting_outcomes.id", ondelete="SET NULL")),
            sa.Column("assignee", sa.String(100)),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("deadline", sa.DateTime(timezone=True)),
            sa.Column("status", sa.String(20), server_default="pending"),
            sa.Column("result", sa.Text()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
            sa.Column("completed_at", sa.DateTime(timezone=True)),
        ],
    )

    _ensure_table(
        "agent_heartbeats",
        [
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("agent_id", sa.String(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column("load_level", sa.Integer(), server_default="0"),
            sa.Column("status_detail", JSONB, server_default="{}"),
        ],
    )

    _add_column("users", sa.Column("notification_config", JSONB, server_default="{}"))
    _add_column("users", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()))
    _add_check_constraint("users", "ck_users_role", "role IN ('user', 'admin')")

    _add_column("projects", sa.Column("tech_stack", sa.String(100)))
    _add_column("projects", sa.Column("deadline", sa.DateTime(timezone=True)))
    _add_column("projects", sa.Column("status", sa.String(20), server_default="created"))
    _add_column("projects", sa.Column("review_group_id", sa.String))
    _add_column("projects", sa.Column("completed_at", sa.DateTime(timezone=True)))
    _add_column("projects", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()))
    _add_check_constraint("projects", "ck_projects_status", "status IN ('created', 'in_progress', 'completed')")
    _create_index("idx_projects_creator", "projects", ["creator_id"])
    _create_index("idx_projects_status", "projects", ["status"])
    _create_index("idx_projects_name", "projects", ["name"])
    if not _constraint_exists("fk_projects_review_group"):
        try:
            op.create_foreign_key("fk_projects_review_group", "projects", "groups", ["review_group_id"], ["id"], ondelete="SET NULL")
        except Exception:
            pass

    _add_column("requirements", sa.Column("confirmed_by", sa.String))
    _add_column("requirements", sa.Column("meeting_id", sa.String))
    _add_column("requirements", sa.Column("attachments", JSONB, server_default="[]"))
    _create_index("idx_requirements_locked", "requirements", ["is_locked"])

    _add_column("agents", sa.Column("discovered_by", sa.String(20), server_default="profile_scan"))
    _add_column("agents", sa.Column("hermes_agent_id", sa.String))
    _add_column("agents", sa.Column("profile_path", sa.String(500)))
    _add_column("agents", sa.Column("last_heartbeat", sa.DateTime(timezone=True)))
    _add_column("agents", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()))
    _add_check_constraint("agents", "ck_agents_type", "agent_type IN ('hermes','trae','codearts','opencode','cursor','claude_code','codebuddy','lingma')")
    _add_check_constraint("agents", "ck_agents_status", "status IN ('online','offline','busy')")
    _add_check_constraint("agents", "ck_agents_discovered_by", "discovered_by IN ('profile_scan','skill_discover')")
    _create_index("idx_agents_type", "agents", ["agent_type"])
    _create_index("idx_agents_status", "agents", ["status"])
    _create_index("idx_agents_hermes", "agents", ["hermes_agent_id"])
    if not _constraint_exists("fk_agents_hermes"):
        try:
            op.create_foreign_key("fk_agents_hermes", "agents", "agents", ["hermes_agent_id"], ["id"], ondelete="SET NULL")
        except Exception:
            pass

    _ensure_table(
        "hermes_skills",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("hermes_agent_id", sa.String(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("config", JSONB, server_default="{}"),
        sa.Column("last_executed_at", sa.DateTime(timezone=True)),
        sa.Column("execution_stats", JSONB, server_default="{}"),
        sa.Column("coding_agent_id", sa.String(), sa.ForeignKey("agents.id", ondelete="SET NULL")),
        sa.Column("task_id", sa.String(), sa.ForeignKey("tasks.id", ondelete="SET NULL")),
        sa.Column("connection_status", sa.String(20)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.CheckConstraint("skill_type IN ('discover_agent','connect_agent','assign_task','receive_message')", name="ck_hermes_skills_type"),
        sa.CheckConstraint("status IN ('active','inactive','error')", name="ck_hermes_skills_status"),
        sa.CheckConstraint("connection_status IN ('connected','disconnected','reconnecting') OR connection_status IS NULL", name="ck_hermes_skills_connection"),
        sa.UniqueConstraint("hermes_agent_id", "skill_type", name="uq_hermes_skills_agent_type"),
    )
    _create_index("idx_hermes_skills_agent", "hermes_skills", ["hermes_agent_id"])
    _create_index("idx_hermes_skills_type", "hermes_skills", ["skill_type"])
    _create_index("idx_hermes_skills_status", "hermes_skills", ["status"])
    _create_index("idx_hermes_skills_coding_agent", "hermes_skills", ["coding_agent_id"])
    _create_index("idx_hermes_skills_task", "hermes_skills", ["task_id"])

    _add_column("tasks", sa.Column("project_id", sa.String))
    _add_column("tasks", sa.Column("name", sa.String(200)))
    _add_column("tasks", sa.Column("type", sa.String(50)))
    _add_column("tasks", sa.Column("agent_type_preference", sa.String(20)))
    _add_column("tasks", sa.Column("assignee_agent_id", sa.String))
    _add_column("tasks", sa.Column("assigned_by_skill_id", sa.String))
    _add_column("tasks", sa.Column("progress", sa.Integer(), server_default="0"))
    _add_column("tasks", sa.Column("progress_message", sa.Text()))
    _add_column("tasks", sa.Column("rejection_count", sa.Integer(), server_default="0"))
    _add_column("tasks", sa.Column("result_summary", sa.Text()))
    _add_column("tasks", sa.Column("artifacts", JSONB, server_default="{}"))
    _add_column("tasks", sa.Column("test_results", JSONB, server_default="{}"))
    _add_column("tasks", sa.Column("context", JSONB, server_default="{}"))
    _add_column("tasks", sa.Column("started_at", sa.DateTime(timezone=True)))
    _add_column("tasks", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()))
    _add_check_constraint("tasks", "ck_tasks_priority", "priority IN ('high','medium','low')")
    _add_check_constraint("tasks", "ck_tasks_status", "status IN ('pending','assigned','running','delivered','accepted','failed','rejected','reassigned')")
    _add_check_constraint("tasks", "ck_tasks_progress", "progress >= 0 AND progress <= 100")
    _create_index("idx_tasks_project", "tasks", ["project_id"])
    _create_index("idx_tasks_type", "tasks", ["type"])
    _create_index("idx_tasks_assigned_skill", "tasks", ["assigned_by_skill_id"])
    if not _constraint_exists("fk_tasks_project"):
        try:
            op.create_foreign_key("fk_tasks_project", "tasks", "projects", ["project_id"], ["id"], ondelete="CASCADE")
            op.create_foreign_key("fk_tasks_assignee_agent", "tasks", "agents", ["assignee_agent_id"], ["id"], ondelete="SET NULL")
            op.create_foreign_key("fk_tasks_assigned_skill", "tasks", "hermes_skills", ["assigned_by_skill_id"], ["id"], ondelete="SET NULL")
        except Exception:
            pass

    _add_check_constraint("task_dependencies", "ck_task_deps_no_self", "source_task_id != target_task_id")

    _ensure_table(
        "agent_execution_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("task_id", sa.String(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("execution_content", sa.Text()),
        sa.Column("result", sa.Text()),
        sa.Column("via_skill_type", sa.String(30)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.CheckConstraint("via_skill_type IN ('discover_agent','connect_agent','assign_task','receive_message') OR via_skill_type IS NULL", name="ck_exec_logs_skill_type"),
    )
    _create_index("idx_exec_logs_task", "agent_execution_logs", ["task_id"])
    _create_index("idx_exec_logs_agent", "agent_execution_logs", ["agent_id"])
    _create_index("idx_exec_logs_skill", "agent_execution_logs", ["via_skill_type"])

    _add_column("acceptance_records", sa.Column("task_id", sa.String))
    _add_column("acceptance_records", sa.Column("reviewer_agent_id", sa.String))
    _add_column("acceptance_records", sa.Column("suggestions", sa.Text()))
    _add_check_constraint("acceptance_records", "ck_acceptance_result", "result IN ('accepted','rejected')")
    if not _constraint_exists("fk_acceptance_task"):
        try:
            op.create_foreign_key("fk_acceptance_task", "acceptance_records", "tasks", ["task_id"], ["id"], ondelete="CASCADE")
            op.create_foreign_key("fk_acceptance_reviewer", "acceptance_records", "agents", ["reviewer_agent_id"], ["id"], ondelete="SET NULL")
        except Exception:
            pass
    _create_index("idx_acceptance_task", "acceptance_records", ["task_id"])

    _ensure_table(
        "notifications_v2",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(20), server_default="platform"),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.CheckConstraint("channel IN ('platform','email','sms')", name="ck_notifications_channel"),
    )
    _create_index("idx_notifications_user", "notifications_v2", ["user_id"])
    _create_index("idx_notifications_read", "notifications_v2", ["user_id", "is_read"])
    _create_index("idx_notifications_project", "notifications_v2", ["project_id"])

    _add_column("agent_heartbeats", sa.Column("via_skill", sa.String(30)))
    _add_check_constraint("agent_heartbeats", "ck_heartbeats_load", "load_level >= 0 AND load_level <= 100")
    _create_index("idx_heartbeats_time", "agent_heartbeats", ["agent_id", "heartbeat_at"])

    _add_column("groups", sa.Column("project_id", sa.String))
    _add_column("groups", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()))
    _add_check_constraint("groups", "ck_groups_mode", "mode IN ('discussion','meeting')")
    _create_index("idx_groups_project", "groups", ["project_id"])
    _create_index("idx_groups_mode", "groups", ["mode"])
    if not _constraint_exists("fk_groups_project"):
        try:
            op.create_foreign_key("fk_groups_project", "groups", "projects", ["project_id"], ["id"], ondelete="SET NULL")
        except Exception:
            pass

    _add_check_constraint("group_messages", "ck_group_msgs_role", "role IN ('user','assistant','system')")
    _create_index("idx_group_msgs_timestamp", "group_messages", ["group_id", "timestamp"])

    _add_column("meeting_outcomes", sa.Column("meeting_type", sa.String(30)))
    _add_column("meeting_outcomes", sa.Column("agenda", JSONB, server_default="[]"))
    _add_check_constraint("meeting_outcomes", "ck_meeting_type", "meeting_type IN ('requirement_review','tech_solution','daily_standup','incident_postmortem')")
    _create_index("idx_meeting_outcomes_group", "meeting_outcomes", ["group_id"])
    _create_index("idx_meeting_outcomes_type", "meeting_outcomes", ["meeting_type"])

    _add_check_constraint("group_tasks", "ck_group_tasks_status", "status IN ('pending','in_progress','completed')")
    _create_index("idx_group_tasks_group", "group_tasks", ["group_id"])
    _create_index("idx_group_tasks_meeting", "group_tasks", ["meeting_id"])
    _create_index("idx_group_tasks_assignee", "group_tasks", ["assignee"])

    _ensure_table(
        "repos",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gitea_repo_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("ssh_url", sa.String(500)),
        sa.Column("http_url", sa.String(500)),
        sa.Column("default_branch", sa.String(100), server_default="main"),
        sa.Column("is_private", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
    )
    _create_index("idx_repos_project", "repos", ["project_id"])
    _create_index("idx_repos_gitea_id", "repos", ["gitea_repo_id"])

    _ensure_table(
        "repo_branches",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("repo_id", sa.String(), sa.ForeignKey("repos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("branch_type", sa.String(20), nullable=False),
        sa.Column("commit_sha", sa.String(40)),
        sa.Column("is_protected", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("source_branch", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("repo_id", "name", name="uq_repo_branch_name"),
    )
    _create_index("idx_branches_repo", "repo_branches", ["repo_id"])
    _create_index("idx_branches_name", "repo_branches", ["repo_id", "name"], unique=True)

    _ensure_table(
        "pull_requests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("repo_id", sa.String(), sa.ForeignKey("repos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("source_branch", sa.String(200), nullable=False),
        sa.Column("target_branch", sa.String(200), nullable=False),
        sa.Column("author", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("reviewers", JSONB, server_default="[]"),
        sa.Column("merged_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
    )
    _create_index("idx_prs_repo", "pull_requests", ["repo_id"])
    _create_index("idx_prs_status", "pull_requests", ["repo_id", "status"])

    _ensure_table(
        "commits",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("repo_id", sa.String(), sa.ForeignKey("repos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sha", sa.String(40), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("author", sa.String(100), nullable=False),
        sa.Column("author_email", sa.String(255)),
        sa.Column("committer", sa.String(100)),
        sa.Column("committer_email", sa.String(255)),
        sa.Column("branch", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
    )
    _create_index("idx_commits_repo", "commits", ["repo_id"])
    _create_index("idx_commits_sha", "commits", ["repo_id", "sha"])
    _create_index("idx_commits_branch", "commits", ["repo_id", "branch"])

    _ensure_table(
        "task_commits",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("task_id", sa.String(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("commit_id", sa.String(), sa.ForeignKey("commits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("task_id", "commit_id", name="uq_task_commits"),
    )
    _create_index("idx_task_commits_task", "task_commits", ["task_id"])
    _create_index("idx_task_commits_commit", "task_commits", ["commit_id"])


def downgrade():
    def _drop_fk(table, name):
        if _constraint_exists(name):
            try:
                op.drop_constraint(name, table, type_="foreignkey")
            except Exception:
                pass

    _drop_fk("tasks", "fk_tasks_assigned_skill")
    _drop_fk("tasks", "fk_tasks_assignee_agent")
    _drop_fk("tasks", "fk_tasks_project")
    _drop_fk("acceptance_records", "fk_acceptance_task")
    _drop_fk("acceptance_records", "fk_acceptance_reviewer")
    _drop_fk("agents", "fk_agents_hermes")
    _drop_fk("projects", "fk_projects_review_group")
    _drop_fk("groups", "fk_groups_project")

    if _table_exists("task_commits"):
        op.drop_table("task_commits")
    if _table_exists("commits"):
        op.drop_table("commits")
    if _table_exists("pull_requests"):
        op.drop_table("pull_requests")
    if _table_exists("repo_branches"):
        op.drop_table("repo_branches")
    if _table_exists("repos"):
        op.drop_table("repos")
    if _table_exists("notifications_v2"):
        op.drop_table("notifications_v2")
    if _table_exists("agent_execution_logs"):
        op.drop_table("agent_execution_logs")
    if _table_exists("hermes_skills"):
        op.drop_table("hermes_skills")
    if _table_exists("group_tasks"):
        op.drop_table("group_tasks")
    if _table_exists("meeting_outcomes"):
        op.drop_table("meeting_outcomes")
    if _table_exists("group_messages"):
        op.drop_table("group_messages")
    if _table_exists("agent_heartbeats"):
        op.drop_table("agent_heartbeats")
    if _table_exists("groups"):
        op.drop_table("groups")
    if _column_exists("agent_heartbeats", "via_skill"):
        op.drop_column("agent_heartbeats", "via_skill")
    if _column_exists("agents", "updated_at"):
        op.drop_column("agents", "updated_at")
    if _column_exists("agents", "last_heartbeat"):
        op.drop_column("agents", "last_heartbeat")
    if _column_exists("agents", "profile_path"):
        op.drop_column("agents", "profile_path")
    if _column_exists("agents", "hermes_agent_id"):
        op.drop_column("agents", "hermes_agent_id")
    if _column_exists("agents", "discovered_by"):
        op.drop_column("agents", "discovered_by")
    if _column_exists("users", "notification_config"):
        op.drop_column("users", "notification_config")
    if _column_exists("users", "updated_at"):
        op.drop_column("users", "updated_at")
    if _column_exists("projects", "updated_at"):
        op.drop_column("projects", "updated_at")
    if _column_exists("projects", "completed_at"):
        op.drop_column("projects", "completed_at")
    if _column_exists("projects", "review_group_id"):
        op.drop_column("projects", "review_group_id")
    if _column_exists("projects", "status"):
        op.drop_column("projects", "status")
    if _column_exists("projects", "deadline"):
        op.drop_column("projects", "deadline")
    if _column_exists("projects", "tech_stack"):
        op.drop_column("projects", "tech_stack")
    if _column_exists("requirements", "attachments"):
        op.drop_column("requirements", "attachments")
    if _column_exists("requirements", "meeting_id"):
        op.drop_column("requirements", "meeting_id")
    if _column_exists("requirements", "confirmed_by"):
        op.drop_column("requirements", "confirmed_by")
    if _column_exists("tasks", "updated_at"):
        op.drop_column("tasks", "updated_at")
    if _column_exists("tasks", "started_at"):
        op.drop_column("tasks", "started_at")
    if _column_exists("tasks", "context"):
        op.drop_column("tasks", "context")
    if _column_exists("tasks", "test_results"):
        op.drop_column("tasks", "test_results")
    if _column_exists("tasks", "artifacts"):
        op.drop_column("tasks", "artifacts")
    if _column_exists("tasks", "result_summary"):
        op.drop_column("tasks", "result_summary")
    if _column_exists("tasks", "rejection_count"):
        op.drop_column("tasks", "rejection_count")
    if _column_exists("tasks", "progress_message"):
        op.drop_column("tasks", "progress_message")
    if _column_exists("tasks", "progress"):
        op.drop_column("tasks", "progress")
    if _column_exists("tasks", "assigned_by_skill_id"):
        op.drop_column("tasks", "assigned_by_skill_id")
    if _column_exists("tasks", "assignee_agent_id"):
        op.drop_column("tasks", "assignee_agent_id")
    if _column_exists("tasks", "agent_type_preference"):
        op.drop_column("tasks", "agent_type_preference")
    if _column_exists("tasks", "type"):
        op.drop_column("tasks", "type")
    if _column_exists("tasks", "name"):
        op.drop_column("tasks", "name")
    if _column_exists("tasks", "project_id"):
        op.drop_column("tasks", "project_id")
    if _column_exists("acceptance_records", "suggestions"):
        op.drop_column("acceptance_records", "suggestions")
    if _column_exists("acceptance_records", "reviewer_agent_id"):
        op.drop_column("acceptance_records", "reviewer_agent_id")
    if _column_exists("acceptance_records", "task_id"):
        op.drop_column("acceptance_records", "task_id")
    if _column_exists("groups", "updated_at"):
        op.drop_column("groups", "updated_at")
    if _column_exists("groups", "project_id"):
        op.drop_column("groups", "project_id")
    if _column_exists("meeting_outcomes", "agenda"):
        op.drop_column("meeting_outcomes", "agenda")
    if _column_exists("meeting_outcomes", "meeting_type"):
        op.drop_column("meeting_outcomes", "meeting_type")
