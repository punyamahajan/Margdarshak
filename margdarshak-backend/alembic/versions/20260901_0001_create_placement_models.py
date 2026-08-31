"""create placement hotline models

Revision ID: 20260901_0001
Revises:
Create Date: 2026-09-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260901_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ticket_status = postgresql.ENUM(
    "open", "escalated", "resolved", name="ticket_status", create_type=False
)
call_flow_type = postgresql.ENUM(
    "triage", "matchmaker_upgrade", name="call_flow_type", create_type=False
)
bridge_status = postgresql.ENUM(
    "active",
    "expired",
    "revealed",
    "upgraded_to_voice",
    name="bridge_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    ticket_status.create(bind, checkfirst=True)
    call_flow_type.create(bind, checkfirst=True)
    bridge_status.create(bind, checkfirst=True)

    op.create_table(
        "students",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("roll_number", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("branch", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("linkedin_url", sa.String(length=2048), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("roll_number"),
    )
    op.create_table(
        "placement_drives",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("poc_name", sa.String(length=255), nullable=False),
        sa.Column("poc_contact", sa.String(length=255), nullable=False),
        sa.Column("policy_doc_ref", sa.String(length=2048), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("drive_id", sa.Uuid(), nullable=True),
        sa.Column("issue_summary", sa.Text(), nullable=False),
        sa.Column("transcript_ref", sa.String(length=2048), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("status", ticket_status, nullable=False),
        sa.Column("escalated_to", sa.String(length=255), nullable=False),
        sa.Column("roll_number_snapshot", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["drive_id"], ["placement_drives.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "case_cards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("structured_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "call_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agora_channel_id", sa.String(length=255), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("flow_type", call_flow_type, nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "chat_bridges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_a_id", sa.Uuid(), nullable=False),
        sa.Column("student_b_id", sa.Uuid(), nullable=False),
        sa.Column("match_reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", bridge_status, nullable=False),
        sa.ForeignKeyConstraint(["student_a_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["student_b_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "consent_reveals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bridge_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column(
            "consented_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bridge_id"], ["chat_bridges.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("consent_reveals")
    op.drop_table("chat_bridges")
    op.drop_table("call_sessions")
    op.drop_table("case_cards")
    op.drop_table("tickets")
    op.drop_table("placement_drives")
    op.drop_table("students")

    bind = op.get_bind()
    bridge_status.drop(bind, checkfirst=True)
    call_flow_type.drop(bind, checkfirst=True)
    ticket_status.drop(bind, checkfirst=True)
