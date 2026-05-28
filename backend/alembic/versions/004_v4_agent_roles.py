"""v4.0: Add 10 named agent roles system

Revision ID: 004
Revises: 003
Create Date: 2026-05-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "004"
down_revision = "003"
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


def _constraint_exists(table, constraint):
    conn = op.get_context().bind
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name=:t AND constraint_name=:c"
        ),
        {"t": table, "c": constraint},
    )
    return result.first() is not None


def upgrade():
    if not _column_exists("agents", "role_name"):
        op.add_column("agents", sa.Column("role_name", sa.String(50), nullable=True))
        op.create_index("idx_agents_role_name", "agents", ["role_name"])

    if not _column_exists("agents", "chinese_name"):
        op.add_column("agents", sa.Column("chinese_name", sa.String(50), nullable=True))

    if not _column_exists("agents", "role_type"):
        op.add_column("agents", sa.Column("role_type", sa.String(30), nullable=True))

    if not _column_exists("agents", "is_named_role"):
        op.add_column("agents", sa.Column("is_named_role", sa.Boolean(), server_default=sa.text("false")))

    if not _column_exists("agents", "managed_swarms"):
        op.add_column("agents", sa.Column("managed_swarms", JSONB(), nullable=True))

    if _constraint_exists("agents", "ck_agents_type"):
        op.drop_constraint("ck_agents_type", "agents", type_="check")

    op.create_check_constraint(
        "ck_agents_type",
        "agents",
        "agent_type IN ('hermes','trae','codearts','opencode','cursor','claude_code','codebuddy','lingma','devika','codex')",
    )


def downgrade():
    if _constraint_exists("agents", "ck_agents_type"):
        op.drop_constraint("ck_agents_type", "agents", type_="check")

    op.create_check_constraint(
        "ck_agents_type",
        "agents",
        "agent_type IN ('hermes','trae','codearts','opencode','cursor','claude_code','codebuddy','lingma','devika')",
    )

    if _column_exists("agents", "managed_swarms"):
        op.drop_column("agents", "managed_swarms")

    if _column_exists("agents", "is_named_role"):
        op.drop_column("agents", "is_named_role")

    if _column_exists("agents", "role_type"):
        op.drop_column("agents", "role_type")

    if _column_exists("agents", "chinese_name"):
        op.drop_column("agents", "chinese_name")

    if _column_exists("agents", "role_name"):
        op.drop_index("idx_agents_role_name", "agents")
        op.drop_column("agents", "role_name")