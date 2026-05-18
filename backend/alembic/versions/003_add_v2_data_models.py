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


def upgrade():
    op.add_column("users", sa.Column("notification_config", JSONB, server_default="{}"))
    op.add_column("users", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()))
    op.execute("ALTER TABLE users ADD CONSTRAINT ck_users_role CHECK (role IN ('user', 'admin'))")

    op.add_column("projects", sa.Column("tech_stack", sa.String(100)))
    op.add_column("projects", sa.Column("deadline", sa.DateTime(timezone=True)))
    op.add_column("projects", sa.Column("status", sa.String(20), server_default="created"))
    op.add_column("projects", sa.Column("review_group_id", sa.String))
    op.add_column("projects", sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.add_column("projects", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()))
    op.execute("ALTER TABLE projects ADD CONSTRAINT ck_projects_status CHECK (status IN ('created', 'in_progress', 'completed'))")
    op.create_index("idx_projects_creator", "projects", ["creator_id"])
    op.create_index("idx_projects_status", "projects", ["status"])
    op.create_index("idx_projects_name", "projects", ["name"])
    try:
        op.create_foreign_key("fk_projects_review_group", "projects", "groups", ["review_group_id"], ["id"], ondelete="SET NULL")
    except Exception:
        pass

    op.add_column("requirements", sa.Column("confirmed_by", sa.String))
    op.add_column("requirements", sa.Column("meeting_id", sa.String))
    op.add_column("requirements", sa.Column("attachments", JSONB, server_default="[]"))
    op.create_index("idx_requirements_locked", "requirements", ["is_locked"])

    op.add_column("agents", sa.Column("discovered_by", sa.String(20), server_default="profile_scan"))
    op.add_column("agents", sa.Column("hermes_agent_id", sa.String))
    op.add_column("agents", sa.Column("profile_path", sa.String(500)))
    op.add_column("agents", sa.Column("last_heartbeat", sa.DateTime(timezone=True)))
    op.add_column("agents", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()))
    op.execute("ALTER TABLE agents ADD CONSTRAINT ck_agents_type CHECK (agent_type IN ('hermes','trae','codearts','opencode','cursor','claude_code','codebuddy','lingma'))")
    op.execute("ALTER TABLE agents ADD CONSTRAINT ck_agents_status CHECK (status IN ('online','offline','busy'))")
    op.execute("ALTER TABLE agents ADD CONSTRAINT ck_agents_discovered_by CHECK (discovered_by IN ('profile_scan','skill_discover'))")
    op.create_index("idx_agents_type", "agents", ["agent_type"])
    op.create_index("idx_agents_status", "agents", ["status"])
    op.create_index("idx_agents_hermes", "agents", ["hermes_agent_id"])
    try:
        op.create_foreign_key("fk_agents_hermes", "agents", "agents", ["hermes_agent_id"], ["id"], ondelete="SET NULL")
    except Exception:
        pass

    op.create_table(
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
    op.create_index("idx_hermes_skills_agent", "hermes_skills", ["hermes_agent_id"])
    op.create_index("idx_hermes_skills_type", "hermes_skills", ["skill_type"])
    op.create_index("idx_hermes_skills_status", "hermes_skills", ["status"])
    op.create_index("idx_hermes_skills_coding_agent", "hermes_skills", ["coding_agent_id"])
    op.create_index("idx_hermes_skills_task", "hermes_skills", ["task_id"])

    op.add_column("tasks", sa.Column("project_id", sa.String))
    op.add_column("tasks", sa.Column("name", sa.String(200)))
    op.add_column("tasks", sa.Column("type", sa.String(50)))
    op.add_column("tasks", sa.Column("agent_type_preference", sa.String(20)))
    op.add_column("tasks", sa.Column("assignee_agent_id", sa.String))
    op.add_column("tasks", sa.Column("assigned_by_skill_id", sa.String))
    op.add_column("tasks", sa.Column("progress", sa.Integer(), server_default="0"))
    op.add_column("tasks", sa.Column("progress_message", sa.Text()))
    op.add_column("tasks", sa.Column("rejection_count", sa.Integer(), server_default="0"))
    op.add_column("tasks", sa.Column("result_summary", sa.Text()))
    op.add_column("tasks", sa.Column("artifacts", JSONB, server_default="{}"))
    op.add_column("tasks", sa.Column("test_results", JSONB, server_default="{}"))
    op.add_column("tasks", sa.Column("context", JSONB, server_default="{}"))
    op.add_column("tasks", sa.Column("started_at", sa.DateTime(timezone=True)))
    op.add_column("tasks", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()))
    op.execute("ALTER TABLE tasks ADD CONSTRAINT ck_tasks_priority CHECK (priority IN ('high','medium','low'))")
    op.execute("ALTER TABLE tasks ADD CONSTRAINT ck_tasks_status CHECK (status IN ('pending','assigned','running','delivered','accepted','failed','rejected','reassigned'))")
    op.execute("ALTER TABLE tasks ADD CONSTRAINT ck_tasks_progress CHECK (progress >= 0 AND progress <= 100)")
    op.create_index("idx_tasks_project", "tasks", ["project_id"])
    op.create_index("idx_tasks_type", "tasks", ["type"])
    op.create_index("idx_tasks_assigned_skill", "tasks", ["assigned_by_skill_id"])
    try:
        op.create_foreign_key("fk_tasks_project", "tasks", "projects", ["project_id"], ["id"], ondelete="CASCADE")
        op.create_foreign_key("fk_tasks_assignee_agent", "tasks", "agents", ["assignee_agent_id"], ["id"], ondelete="SET NULL")
        op.create_foreign_key("fk_tasks_assigned_skill", "tasks", "hermes_skills", ["assigned_by_skill_id"], ["id"], ondelete="SET NULL")
    except Exception:
        pass

    op.execute("ALTER TABLE task_dependencies ADD CONSTRAINT ck_task_deps_no_self CHECK (source_task_id != target_task_id)")

    op.create_table(
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
    op.create_index("idx_exec_logs_task", "agent_execution_logs", ["task_id"])
    op.create_index("idx_exec_logs_agent", "agent_execution_logs", ["agent_id"])
    op.create_index("idx_exec_logs_skill", "agent_execution_logs", ["via_skill_type"])

    op.add_column("acceptance_records", sa.Column("task_id", sa.String))
    op.add_column("acceptance_records", sa.Column("reviewer_agent_id", sa.String))
    op.add_column("acceptance_records", sa.Column("suggestions", sa.Text()))
    op.execute("ALTER TABLE acceptance_records ADD CONSTRAINT ck_acceptance_result CHECK (result IN ('accepted','rejected'))")
    try:
        op.create_foreign_key("fk_acceptance_task", "acceptance_records", "tasks", ["task_id"], ["id"], ondelete="CASCADE")
        op.create_foreign_key("fk_acceptance_reviewer", "acceptance_records", "agents", ["reviewer_agent_id"], ["id"], ondelete="SET NULL")
    except Exception:
        pass
    op.create_index("idx_acceptance_task", "acceptance_records", ["task_id"])

    op.create_table(
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
    op.create_index("idx_notifications_user", "notifications_v2", ["user_id"])
    op.create_index("idx_notifications_read", "notifications_v2", ["user_id", "is_read"])
    op.create_index("idx_notifications_project", "notifications_v2", ["project_id"])

    op.add_column("agent_heartbeats", sa.Column("via_skill", sa.String(30)))
    op.execute("ALTER TABLE agent_heartbeats ADD CONSTRAINT ck_heartbeats_load CHECK (load_level >= 0 AND load_level <= 100)")
    op.create_index("idx_heartbeats_time", "agent_heartbeats", ["agent_id", "heartbeat_at"])

    op.add_column("groups", sa.Column("project_id", sa.String))
    op.add_column("groups", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()))
    op.execute("ALTER TABLE groups ADD CONSTRAINT ck_groups_mode CHECK (mode IN ('discussion','meeting'))")
    op.create_index("idx_groups_project", "groups", ["project_id"])
    op.create_index("idx_groups_mode", "groups", ["mode"])
    try:
        op.create_foreign_key("fk_groups_project", "groups", "projects", ["project_id"], ["id"], ondelete="SET NULL")
    except Exception:
        pass

    op.execute("ALTER TABLE group_messages ADD CONSTRAINT ck_group_msgs_role CHECK (role IN ('user','assistant','system'))")
    op.create_index("idx_group_msgs_timestamp", "group_messages", ["group_id", "timestamp"])

    op.add_column("meeting_outcomes", sa.Column("meeting_type", sa.String(30)))
    op.add_column("meeting_outcomes", sa.Column("agenda", JSONB, server_default="[]"))
    op.execute("ALTER TABLE meeting_outcomes ADD CONSTRAINT ck_meeting_type CHECK (meeting_type IN ('requirement_review','tech_solution','daily_standup','incident_postmortem'))")
    op.create_index("idx_meeting_outcomes_group", "meeting_outcomes", ["group_id"])
    op.create_index("idx_meeting_outcomes_type", "meeting_outcomes", ["meeting_type"])

    op.execute("ALTER TABLE group_tasks ADD CONSTRAINT ck_group_tasks_status CHECK (status IN ('pending','in_progress','completed'))")
    op.create_index("idx_group_tasks_group", "group_tasks", ["group_id"])
    op.create_index("idx_group_tasks_meeting", "group_tasks", ["meeting_id"])
    op.create_index("idx_group_tasks_assignee", "group_tasks", ["assignee"])

    op.create_table(
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
    op.create_index("idx_repos_project", "repos", ["project_id"])
    op.create_index("idx_repos_gitea_id", "repos", ["gitea_repo_id"])

    op.create_table(
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
    op.create_index("idx_branches_repo", "repo_branches", ["repo_id"])
    op.create_index("idx_branches_name", "repo_branches", ["repo_id", "name"], unique=True)

    op.create_table(
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
    op.create_index("idx_prs_repo", "pull_requests", ["repo_id"])
    op.create_index("idx_prs_status", "pull_requests", ["repo_id", "status"])

    op.create_table(
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
    op.create_index("idx_commits_repo", "commits", ["repo_id"])
    op.create_index("idx_commits_sha", "commits", ["repo_id", "sha"])
    op.create_index("idx_commits_branch", "commits", ["repo_id", "branch"])

    op.create_table(
        "task_commits",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("task_id", sa.String(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("commit_id", sa.String(), sa.ForeignKey("commits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("task_id", "commit_id", name="uq_task_commits"),
    )
    op.create_index("idx_task_commits_task", "task_commits", ["task_id"])
    op.create_index("idx_task_commits_commit", "task_commits", ["commit_id"])


def downgrade():
    op.drop_table("task_commits")
    op.drop_table("commits")
    op.drop_table("pull_requests")
    op.drop_table("repo_branches")
    op.drop_table("repos")
    op.drop_table("notifications_v2")
    op.drop_table("agent_execution_logs")
    op.drop_table("hermes_skills")
    op.drop_column("agent_heartbeats", "via_skill")
    op.drop_column("agents", "updated_at")
    op.drop_column("agents", "last_heartbeat")
    op.drop_column("agents", "profile_path")
    op.drop_column("agents", "hermes_agent_id")
    op.drop_column("agents", "discovered_by")
    op.drop_column("users", "notification_config")
    op.drop_column("users", "updated_at")
    op.drop_column("projects", "updated_at")
    op.drop_column("projects", "completed_at")
    op.drop_column("projects", "review_group_id")
    op.drop_column("projects", "status")
    op.drop_column("projects", "deadline")
    op.drop_column("projects", "tech_stack")
    op.drop_column("requirements", "attachments")
    op.drop_column("requirements", "meeting_id")
    op.drop_column("requirements", "confirmed_by")
    op.drop_column("tasks", "updated_at")
    op.drop_column("tasks", "started_at")
    op.drop_column("tasks", "context")
    op.drop_column("tasks", "test_results")
    op.drop_column("tasks", "artifacts")
    op.drop_column("tasks", "result_summary")
    op.drop_column("tasks", "rejection_count")
    op.drop_column("tasks", "progress_message")
    op.drop_column("tasks", "progress")
    op.drop_column("tasks", "assigned_by_skill_id")
    op.drop_column("tasks", "assignee_agent_id")
    op.drop_column("tasks", "agent_type_preference")
    op.drop_column("tasks", "type")
    op.drop_column("tasks", "name")
    op.drop_column("tasks", "project_id")
    op.drop_column("acceptance_records", "suggestions")
    op.drop_column("acceptance_records", "reviewer_agent_id")
    op.drop_column("acceptance_records", "task_id")
    op.drop_column("groups", "updated_at")
    op.drop_column("groups", "project_id")
    op.drop_column("meeting_outcomes", "agenda")
    op.drop_column("meeting_outcomes", "meeting_type")
