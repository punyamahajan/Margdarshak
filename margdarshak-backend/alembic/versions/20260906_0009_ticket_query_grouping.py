"""Add ticket query grouping fields for semantic deduplication.

Revision ID: 20260906_0009
Revises: 20260905_0010
"""

from alembic import op
import sqlalchemy as sa

revision: str = "20260906_0009"
down_revision: str | None = "20260905_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column("parent_ticket_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "tickets",
        sa.Column(
            "similar_count",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.create_foreign_key(
        "fk_tickets_parent_ticket_id",
        "tickets",
        "tickets",
        ["parent_ticket_id"],
        ["id"],
    )
    op.create_index(
        "ix_tickets_parent_ticket_id",
        "tickets",
        ["parent_ticket_id"],
    )
    op.alter_column("tickets", "similar_count", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_tickets_parent_ticket_id", table_name="tickets")
    op.drop_constraint("fk_tickets_parent_ticket_id", "tickets", type_="foreignkey")
    op.drop_column("tickets", "similar_count")
    op.drop_column("tickets", "parent_ticket_id")
