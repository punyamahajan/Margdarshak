"""add resource diagnostic tables

Revision ID: 20260902_0005
Revises: 20260902_0004
Create Date: 2026-09-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260902_0005"
down_revision: str | None = "20260902_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

resource_format = postgresql.ENUM(
    "video", "sheet", name="resource_format", create_type=False
)
resource_pacing = postgresql.ENUM(
    "short", "long", name="resource_pacing", create_type=False
)
resource_price_tier = postgresql.ENUM(
    "free", "paid", name="resource_price_tier", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    resource_format.create(bind, checkfirst=True)
    resource_pacing.create(bind, checkfirst=True)
    resource_price_tier.create(bind, checkfirst=True)

    op.create_table(
        "resources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("skill_tag", sa.String(length=100), nullable=False),
        sa.Column("format", resource_format, nullable=False),
        sa.Column("pacing", resource_pacing, nullable=False),
        sa.Column("price_tier", resource_price_tier, nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index(op.f("ix_resources_skill_tag"), "resources", ["skill_tag"])

    op.create_table(
        "resource_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("reasoning_snapshot", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_resource_recommendations_resource_id"),
        "resource_recommendations",
        ["resource_id"],
    )
    op.create_index(
        op.f("ix_resource_recommendations_session_id"),
        "resource_recommendations",
        ["session_id"],
    )
    op.create_index(
        op.f("ix_resource_recommendations_student_id"),
        "resource_recommendations",
        ["student_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_resource_recommendations_student_id"),
        table_name="resource_recommendations",
    )
    op.drop_index(
        op.f("ix_resource_recommendations_session_id"),
        table_name="resource_recommendations",
    )
    op.drop_index(
        op.f("ix_resource_recommendations_resource_id"),
        table_name="resource_recommendations",
    )
    op.drop_table("resource_recommendations")
    op.drop_index(op.f("ix_resources_skill_tag"), table_name="resources")
    op.drop_table("resources")

    resource_price_tier.drop(op.get_bind(), checkfirst=True)
    resource_pacing.drop(op.get_bind(), checkfirst=True)
    resource_format.drop(op.get_bind(), checkfirst=True)
