import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.student import Student


class CallFlowType(str, enum.Enum):
    TRIAGE = "triage"
    MATCHMAKER_UPGRADE = "matchmaker_upgrade"


class CallSession(Base):
    __tablename__ = "call_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agora_channel_id: Mapped[str] = mapped_column(String(255))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    flow_type: Mapped[CallFlowType] = mapped_column(
        Enum(CallFlowType, name="call_flow_type", values_callable=lambda e: [x.value for x in e])
    )

    student: Mapped["Student"] = relationship(back_populates="call_sessions")
