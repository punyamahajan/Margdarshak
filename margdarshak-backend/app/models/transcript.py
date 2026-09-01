import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.call_session import CallSession


class TranscriptSpeaker(str, enum.Enum):
    STUDENT = "student"
    AGENT = "agent"
    HUMAN_COORDINATOR = "human_coordinator"


class Transcript(Base):
    __tablename__ = "transcripts"
    __table_args__ = (
        UniqueConstraint(
            "call_session_id", "turn_index", name="uq_transcript_session_turn"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    call_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("call_sessions.id", ondelete="CASCADE"), index=True
    )
    turn_index: Mapped[int] = mapped_column(Integer)
    speaker: Mapped[TranscriptSpeaker] = mapped_column(
        Enum(
            TranscriptSpeaker,
            name="transcript_speaker",
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    call_session: Mapped["CallSession"] = relationship(back_populates="transcripts")
