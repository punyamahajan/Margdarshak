"""Store the runtime Agora agent ID on call sessions.

Revision ID: 20260902_0007
Revises: 20260902_0006
"""

from alembic import op
import sqlalchemy as sa

revision: str = "20260902_0007"
down_revision: str | None = "20260902_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "call_sessions",
        sa.Column("agora_agent_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("call_sessions", "agora_agent_id")
