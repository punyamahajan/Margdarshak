import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.call_session import CallSession
    from app.models.chat_bridge import ChatBridge
    from app.models.consent_reveal import ConsentReveal
    from app.models.ticket import Ticket
    from app.models.resource import ResourceRecommendation


class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    roll_number: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320))
    branch: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(30))
    linkedin_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    matchmaking_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="student")
    call_sessions: Mapped[list["CallSession"]] = relationship(back_populates="student")
    bridges_as_a: Mapped[list["ChatBridge"]] = relationship(
        back_populates="student_a", foreign_keys="ChatBridge.student_a_id"
    )
    bridges_as_b: Mapped[list["ChatBridge"]] = relationship(
        back_populates="student_b", foreign_keys="ChatBridge.student_b_id"
    )
    consent_reveals: Mapped[list["ConsentReveal"]] = relationship(
        back_populates="student"
    )
    resource_recommendations: Mapped[list["ResourceRecommendation"]] = relationship(
        back_populates="student"
    )
