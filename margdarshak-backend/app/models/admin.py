import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TicketCluster(Base):
    __tablename__ = "ticket_clusters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255))
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    drive_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("placement_drives.id"), nullable=True)
    urgency: Mapped[str] = mapped_column(String(30), default="medium")
    status: Mapped[str] = mapped_column(String(30), default="open")
    incident_update: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TicketWorkflow(Base):
    __tablename__ = "ticket_workflows"

    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), default="open")
    assigned_coordinator: Mapped[str | None] = mapped_column(String(255), nullable=True)
    urgency: Mapped[str] = mapped_column(String(30), default="medium")
    language: Mapped[str] = mapped_column(String(50), default="English")
    category: Mapped[str] = mapped_column(String(100), default="Other")
    original_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    conversation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ticket_clusters.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255))
    document_type: Mapped[str] = mapped_column(String(80))
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    drive_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("placement_drives.id"), nullable=True)
    version_label: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    source_reference: Mapped[str] = mapped_column(String(2048))
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ShortlistRecord(Base):
    __tablename__ = "shortlist_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    knowledge_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_documents.id"))
    student_name: Mapped[str] = mapped_column(String(255))
    enrollment_number: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(320))
    company_name: Mapped[str] = mapped_column(String(255))
    drive_id: Mapped[str] = mapped_column(String(100))
    shortlisted: Mapped[bool] = mapped_column(default=True)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    round: Mapped[str | None] = mapped_column(String(255), nullable=True)


class StudentNotification(Base):
    __tablename__ = "student_notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
