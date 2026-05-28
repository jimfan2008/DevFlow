"""v4.0: Add swarm, security audit, and doc version tables

Revision ID: 006
Revises: 005
Create Date: 2026-05-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


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
    if not _table_exists("swarms"):
        op.create_table(
            "swarms",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("manager_agent_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("purpose", sa.String(20), nullable=False),
            sa.Column("step_number", sa.Integer(), nullable=False),
            sa.Column("members", JSONB(), nullable=False, server_default="[]"),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("disbanded_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["manager_agent_id"], ["agents.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_swarms_project", "swarms", ["project_id"])

    if not _table_exists("swarm_tasks"):
        op.create_table(
            "swarm_tasks",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("swarm_id", sa.Integer(), nullable=False),
            sa.Column("task_id", sa.String(), nullable=False),
            sa.Column("assigned_agent_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["swarm_id"], ["swarms.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["assigned_agent_id"], ["agents.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists("security_audits"):
        op.create_table(
            "security_audits",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("auditor_agent_id", sa.String(), nullable=False),
            sa.Column("code_audit_result", JSONB(), nullable=True),
            sa.Column("compliance_result", JSONB(), nullable=True),
            sa.Column("penetration_test_result", JSONB(), nullable=True),
            sa.Column("vulnerabilities_found", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("vulnerabilities_fixed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("overall_status", sa.String(20), nullable=False, server_default="in_progress"),
            sa.Column("report_content", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["auditor_agent_id"], ["agents.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_security_audits_project", "security_audits", ["project_id"])

    if not _table_exists("doc_versions"):
        op.create_table(
            "doc_versions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("doc_type", sa.String(50), nullable=False),
            sa.Column("version", sa.String(20), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("is_consistent", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("last_modified_by", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["last_modified_by"], ["agents.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_doc_versions_project", "doc_versions", ["project_id"])


def downgrade():
    if _table_exists("doc_versions"):
        op.drop_index("idx_doc_versions_project", "doc_versions")
        op.drop_table("doc_versions")

    if _table_exists("security_audits"):
        op.drop_index("idx_security_audits_project", "security_audits")
        op.drop_table("security_audits")

    if _table_exists("swarm_tasks"):
        op.drop_table("swarm_tasks")

    if _table_exists("swarms"):
        op.drop_index("idx_swarms_project", "swarms")
        op.drop_table("swarms")