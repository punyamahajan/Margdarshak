import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.student import Student


class ResourceFormat(str, enum.Enum):
    VIDEO = "video"
    SHEET = "sheet"


class ResourcePacing(str, enum.Enum):
    SHORT = "short"
    LONG = "long"


class ResourcePriceTier(str, enum.Enum):
    FREE = "free"
    PAID = "paid"


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    skill_tag: Mapped[str] = mapped_column(String(100), index=True)
    format: Mapped[ResourceFormat] = mapped_column(
        Enum(
            ResourceFormat,
            name="resource_format",
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    pacing: Mapped[ResourcePacing] = mapped_column(
        Enum(
            ResourcePacing,
            name="resource_pacing",
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    price_tier: Mapped[ResourcePriceTier] = mapped_column(
        Enum(
            ResourcePriceTier,
            name="resource_price_tier",
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    url: Mapped[str] = mapped_column(String(2048), unique=True)
    title: Mapped[str] = mapped_column(String(255))

    recommendations: Mapped[list["ResourceRecommendation"]] = relationship(
        back_populates="resource"
    )


class ResourceRecommendation(Base):
    __tablename__ = "resource_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), index=True)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resources.id"), index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(index=True)
    reasoning_snapshot: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    student: Mapped["Student"] = relationship(back_populates="resource_recommendations")
    resource: Mapped["Resource"] = relationship(back_populates="recommendations")
