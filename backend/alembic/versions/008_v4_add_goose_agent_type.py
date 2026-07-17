"""v4.0: Add goose, atom agent types to ck_agents_type constraint

Revision ID: 008
Revises: 007
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


AGENT_TYPES = (
    "'hermes','trae','codearts','opencode','cursor','claude_code',"
    "'codebuddy','lingma','devika','codex','pi_coding_agent',"
    "'reasonix','codeium','aider-chat','openhands','goose','atom'"
)


def _constraint_exists(table, constraint):
    conn = op.get_context().bind
    try:
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.table_constraints "
                "WHERE table_name=:t AND constraint_name=:c"
            ),
            {"t": table, "c": constraint},
        )
        return result.first() is not None
    except Exception:
        return False


def upgrade():
    if _constraint_exists("agents", "ck_agents_type"):
        op.drop_constraint("ck_agents_type", "agents", type_="check")
    op.create_check_constraint(
        "ck_agents_type",
        "agents",
        f"agent_type IN ({AGENT_TYPES})",
    )


def downgrade():
    if _constraint_exists("agents", "ck_agents_type"):
        op.drop_constraint("ck_agents_type", "agents", type_="check")
    op.create_check_constraint(
        "ck_agents_type",
        "agents",
        "agent_type IN ('hermes','trae','codearts','opencode','cursor','claude_code','codebuddy','lingma','devika','codex','pi_coding_agent','reasonix','codeium','aider-chat','openhands')",
    )
