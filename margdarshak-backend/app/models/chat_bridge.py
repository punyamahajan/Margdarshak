import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.consent_reveal import ConsentReveal
    from app.models.student import Student


class BridgeStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVEALED = "revealed"
    UPGRADED_TO_VOICE = "upgraded_to_voice"


class ChatBridge(Base):
    __tablename__ = "chat_bridges"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_a_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    student_b_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    match_reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[BridgeStatus] = mapped_column(
        Enum(BridgeStatus, name="bridge_status", values_callable=lambda e: [x.value for x in e])
    )

    student_a: Mapped["Student"] = relationship(
        back_populates="bridges_as_a", foreign_keys=[student_a_id]
    )
    student_b: Mapped["Student"] = relationship(
        back_populates="bridges_as_b", foreign_keys=[student_b_id]
    )
    consent_reveals: Mapped[list["ConsentReveal"]] = relationship(back_populates="bridge")
