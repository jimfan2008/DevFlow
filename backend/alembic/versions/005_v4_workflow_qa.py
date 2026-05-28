"""v4.0: Add 16-step workflow and QA gating tables

Revision ID: 005
Revises: 004
Create Date: 2026-05-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "005"
down_revision = "004"
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
    return result.first() is not None


def _table_exists(table):
    conn = op.get_context().bind
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name=:t"
        ),
        {"t": table},
    )
    return result.first() is not None


def upgrade():
    if not _table_exists("workflow_steps"):
        op.create_table(
            "workflow_steps",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("step_number", sa.Integer(), nullable=False),
            sa.Column("step_name", sa.String(200), nullable=False),
            sa.Column("executor_agent_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("input_artifacts", JSONB(), nullable=True),
            sa.Column("output_artifacts", JSONB(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["executor_agent_id"], ["agents.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_workflow_steps_project", "workflow_steps", ["project_id"])

    if not _table_exists("qa_records"):
        op.create_table(
            "qa_records",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("workflow_step_id", sa.Integer(), nullable=False),
            sa.Column("task_id", sa.String(), nullable=True),
            sa.Column("qa_agent_id", sa.String(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("review_dimensions", JSONB(), nullable=True),
            sa.Column("problem_details", sa.Text(), nullable=True),
            sa.Column("fix_suggestions", sa.Text(), nullable=True),
            sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["workflow_step_id"], ["workflow_steps.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["qa_agent_id"], ["agents.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_qa_records_project", "qa_records", ["project_id"])

    if not _column_exists("projects", "current_step"):
        op.add_column("projects", sa.Column("current_step", sa.Integer(), nullable=False, server_default="1"))

    if not _column_exists("projects", "core_goal"):
        op.add_column("projects", sa.Column("core_goal", sa.Text(), nullable=True))


def downgrade():
    if _column_exists("projects", "core_goal"):
        op.drop_column("projects", "core_goal")

    if _column_exists("projects", "current_step"):
        op.drop_column("projects", "current_step")

    if _table_exists("qa_records"):
        op.drop_index("idx_qa_records_project", "qa_records")
        op.drop_table("qa_records")

    if _table_exists("workflow_steps"):
        op.drop_index("idx_workflow_steps_project", "workflow_steps")
        op.drop_table("workflow_steps")