"""add consent purpose

Revision ID: 20260901_0003
Revises: 20260901_0002
Create Date: 2026-09-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260901_0003"
down_revision: str | None = "20260901_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

consent_purpose = postgresql.ENUM(
    "reveal", "voice_upgrade", name="consent_purpose", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    consent_purpose.create(bind, checkfirst=True)
    op.add_column(
        "consent_reveals",
        sa.Column(
            "consent_purpose",
            consent_purpose,
            server_default="reveal",
            nullable=False,
        ),
    )
    op.alter_column("consent_reveals", "consent_purpose", server_default=None)
    op.create_unique_constraint(
        "uq_bridge_consent",
        "consent_reveals",
        ["bridge_id", "student_id", "consent_purpose"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_bridge_consent", "consent_reveals", type_="unique")
    op.drop_column("consent_reveals", "consent_purpose")
    consent_purpose.drop(op.get_bind(), checkfirst=True)
