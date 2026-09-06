"""Add student auth and profile fields: password_hash, known_subjects, explore_topics.

Revision ID: 20260906_0010
Revises: 20260906_0009
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260906_0010"
down_revision: str | None = "20260906_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "students",
        sa.Column(
            "known_subjects",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )
    op.add_column(
        "students",
        sa.Column(
            "explore_topics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )
    op.alter_column("students", "known_subjects", server_default=None)
    op.alter_column("students", "explore_topics", server_default=None)


def downgrade() -> None:
    op.drop_column("students", "explore_topics")
    op.drop_column("students", "known_subjects")
    op.drop_column("students", "password_hash")
