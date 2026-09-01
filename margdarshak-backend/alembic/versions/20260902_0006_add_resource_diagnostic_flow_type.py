"""add resource diagnostic call flow type

Revision ID: 20260902_0006
Revises: 20260902_0005
Create Date: 2026-09-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260902_0006"
down_revision: str | None = "20260902_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE call_flow_type ADD VALUE IF NOT EXISTS 'resource_diagnostic'"
    )


def downgrade() -> None:
    # PostgreSQL cannot remove an enum value safely without recreating the type.
    # Retaining an unused value is safer than rewriting call_sessions on downgrade.
    pass
