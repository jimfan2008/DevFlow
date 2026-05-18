"""add srs tables (agents, requirements, task_executions, acceptance_records)

Revision ID: 002
Revises: 001
Create Date: 2026-05-15

"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------
    # 1. agents — 编程 Agent 表 (SRS §3.3)
    # ------------------------------------------------------------------
    op.create_table(
        "agents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="offline"),
        sa.Column("api_endpoint", sa.String(500)),
        sa.Column("config", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("name", name="uq_agents_name"),
    )

    # ------------------------------------------------------------------
    # 2. requirements — 需求表 (SRS §3.1)
    # ------------------------------------------------------------------
    op.create_table(
        "requirements",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(),
                   sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("is_locked", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("confirmed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Index("idx_requirements_project", "project_id"),
    )

    # ------------------------------------------------------------------
    # 3. task_executions — 任务执行表 (SRS §3.3.2)
    # ------------------------------------------------------------------
    op.create_table(
        "task_executions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("task_id", sa.String(),
                   sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(),
                   sa.ForeignKey("agents.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("execution_log", sa.Text()),
        sa.Column("result_summary", sa.JSON()),
        sa.Column("problem_details", sa.JSON()),
        sa.Column("delivered_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Index("idx_task_executions_task", "task_id"),
        sa.Index("idx_task_executions_agent", "agent_id"),
        sa.Index("idx_task_executions_status", "status"),
    )

    # ------------------------------------------------------------------
    # 4a. tasks — 补充 acceptance_criteria 列 (SRS §3.2.1)
    # ------------------------------------------------------------------
    op.add_column("tasks", sa.Column("acceptance_criteria", sa.Text()))

    # ------------------------------------------------------------------
    # 5. acceptance_records — 验收记录表 (SRS §3.4)
    # ------------------------------------------------------------------
    op.create_table(
        "acceptance_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("task_execution_id", sa.String(),
                   sa.ForeignKey("task_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("result", sa.String(10), nullable=False),
        sa.Column("problem_details", sa.JSON()),
        sa.Column("reviewer", sa.String(100), server_default="Hermes Agent"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Index("idx_acceptance_records_execution", "task_execution_id"),
    )


def downgrade():
    op.drop_column("tasks", "acceptance_criteria")
    op.drop_table("acceptance_records")
    op.drop_table("task_executions")
    op.drop_table("requirements")
    op.drop_table("agents")