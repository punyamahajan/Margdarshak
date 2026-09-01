"""add transcript storage

Revision ID: 20260902_0004
Revises: 20260901_0003
Create Date: 2026-09-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260902_0004"
down_revision: str | None = "20260901_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

transcript_speaker = postgresql.ENUM(
    "student",
    "agent",
    "human_coordinator",
    name="transcript_speaker",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    transcript_speaker.create(bind, checkfirst=True)
    op.create_table(
        "transcripts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("call_session_id", sa.Uuid(), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("speaker", transcript_speaker, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["call_session_id"], ["call_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "call_session_id", "turn_index", name="uq_transcript_session_turn"
        ),
    )
    op.create_index(
        op.f("ix_transcripts_call_session_id"),
        "transcripts",
        ["call_session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transcripts_call_session_id"), table_name="transcripts")
    op.drop_table("transcripts")
    transcript_speaker.drop(op.get_bind(), checkfirst=True)
