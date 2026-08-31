import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.chat_bridge import ChatBridge
    from app.models.student import Student


class ConsentPurpose(str, enum.Enum):
    REVEAL = "reveal"
    VOICE_UPGRADE = "voice_upgrade"


class ConsentReveal(Base):
    __tablename__ = "consent_reveals"
    __table_args__ = (
        UniqueConstraint(
            "bridge_id", "student_id", "consent_purpose", name="uq_bridge_consent"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bridge_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_bridges.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    consent_purpose: Mapped[ConsentPurpose] = mapped_column(
        Enum(
            ConsentPurpose,
            name="consent_purpose",
            values_callable=lambda values: [value.value for value in values],
        )
    )
    consented_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    bridge: Mapped["ChatBridge"] = relationship(back_populates="consent_reveals")
    student: Mapped["Student"] = relationship(back_populates="consent_reveals")
