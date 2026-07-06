"""v4.0: Add tdd_test_cases table for granular test case storage and per-row QA

Revision ID: 007
Revises: 006
Create Date: 2026-07-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "007"
down_revision = "006"
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
    if not _table_exists("tdd_test_cases"):
        op.create_table(
            "tdd_test_cases",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("workflow_step_id", sa.Integer(), nullable=True),
            sa.Column("round_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("case_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("case_id", sa.String(50), nullable=False),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("precondition", sa.Text(), nullable=True),
            sa.Column("test_steps", sa.Text(), nullable=True),
            sa.Column("expected_result", sa.Text(), nullable=True),
            sa.Column("priority", sa.String(20), nullable=True),
            sa.Column("category", sa.String(100), nullable=True),
            sa.Column("source_section", sa.String(200), nullable=True),
            sa.Column("qa_status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
            sa.Column("qa_score", sa.Integer(), nullable=True),
            sa.Column("qa_feedback", sa.Text(), nullable=True),
            sa.Column("qa_detail", sa.Text(), nullable=True),
            sa.Column("fix_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("metadata_json", JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["workflow_step_id"], ["workflow_steps.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_tdd_test_cases_project_id", "tdd_test_cases", ["project_id"])
        op.create_index("ix_tdd_test_cases_project_round", "tdd_test_cases", ["project_id", "round_number"])


def downgrade():
    op.drop_table("tdd_test_cases")
