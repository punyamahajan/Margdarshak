import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.case_card import CaseCard
    from app.models.placement_drive import PlacementDrive
    from app.models.student import Student


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    drive_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("placement_drives.id"), nullable=True
    )
    issue_summary: Mapped[str] = mapped_column(Text)
    transcript_ref: Mapped[str] = mapped_column(String(2048))
    confidence_score: Mapped[float] = mapped_column(Float)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status", values_callable=lambda e: [x.value for x in e])
    )
    escalated_to: Mapped[str] = mapped_column(String(255))
    roll_number_snapshot: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    student: Mapped["Student"] = relationship(back_populates="tickets")
    drive: Mapped["PlacementDrive | None"] = relationship(back_populates="tickets")
    case_cards: Mapped[list["CaseCard"]] = relationship(back_populates="ticket")
