"""Add the student's university to their profile.

Revision ID: 20260903_0008
Revises: 20260902_0007
"""

from alembic import op
import sqlalchemy as sa

revision: str = "20260903_0008"
down_revision: str | None = "20260902_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column(
            "university",
            sa.String(length=255),
            nullable=False,
            server_default="Aarohan Demo University",
        ),
    )
    op.alter_column("students", "university", server_default=None)


def downgrade() -> None:
    op.drop_column("students", "university")
