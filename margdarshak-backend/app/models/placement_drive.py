import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ticket import Ticket


class PlacementDrive(Base):
    """Externally synced entity; application code must treat this model as read-only."""

    __tablename__ = "placement_drives"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(255))
    poc_name: Mapped[str] = mapped_column(String(255))
    poc_contact: Mapped[str] = mapped_column(String(255))
    policy_doc_ref: Mapped[str] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(50))

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="drive")
