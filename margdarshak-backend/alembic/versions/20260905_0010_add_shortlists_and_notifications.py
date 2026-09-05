"""Add imported shortlist records and coordinator notifications.

Revision ID: 20260905_0010
Revises: 20260905_0009
"""
from alembic import op
import sqlalchemy as sa

revision = "20260905_0010"
down_revision = "20260905_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("shortlist_records", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("knowledge_document_id", sa.Uuid(), sa.ForeignKey("knowledge_documents.id"), nullable=False), sa.Column("student_name", sa.String(255), nullable=False), sa.Column("enrollment_number", sa.String(50), nullable=False), sa.Column("email", sa.String(320), nullable=False), sa.Column("company_name", sa.String(255), nullable=False), sa.Column("drive_id", sa.String(100), nullable=False), sa.Column("shortlisted", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("role", sa.String(255)), sa.Column("round", sa.String(255)))
    op.create_table("student_notifications", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("student_id", sa.Uuid(), sa.ForeignKey("students.id"), nullable=False), sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id")), sa.Column("title", sa.String(255), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    op.drop_table("student_notifications")
    op.drop_table("shortlist_records")
