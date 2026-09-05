"""Add coordinator workflow, clusters, and knowledge library.

Revision ID: 20260905_0009
Revises: 20260903_0008
"""
from alembic import op
import sqlalchemy as sa

revision = "20260905_0009"
down_revision = "20260903_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("ticket_clusters", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("title", sa.String(255), nullable=False), sa.Column("company_name", sa.String(255)), sa.Column("drive_id", sa.Uuid(), sa.ForeignKey("placement_drives.id")), sa.Column("urgency", sa.String(30), nullable=False, server_default="medium"), sa.Column("status", sa.String(30), nullable=False, server_default="open"), sa.Column("incident_update", sa.Text()), sa.Column("response_draft", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("ticket_workflows", sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id"), primary_key=True), sa.Column("status", sa.String(30), nullable=False, server_default="open"), sa.Column("assigned_coordinator", sa.String(255)), sa.Column("urgency", sa.String(30), nullable=False, server_default="medium"), sa.Column("language", sa.String(50), nullable=False, server_default="English"), sa.Column("category", sa.String(100), nullable=False, server_default="Other"), sa.Column("original_request", sa.Text()), sa.Column("conversation_summary", sa.Text()), sa.Column("cluster_id", sa.Uuid(), sa.ForeignKey("ticket_clusters.id")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("knowledge_documents", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("title", sa.String(255), nullable=False), sa.Column("document_type", sa.String(80), nullable=False), sa.Column("company_name", sa.String(255)), sa.Column("drive_id", sa.Uuid(), sa.ForeignKey("placement_drives.id")), sa.Column("version_label", sa.String(100), nullable=False), sa.Column("status", sa.String(30), nullable=False, server_default="draft"), sa.Column("source_reference", sa.String(2048), nullable=False), sa.Column("content", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    op.drop_table("knowledge_documents")
    op.drop_table("ticket_workflows")
    op.drop_table("ticket_clusters")
