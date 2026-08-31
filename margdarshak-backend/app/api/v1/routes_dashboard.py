from collections import Counter

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.chat_bridge import BridgeStatus, ChatBridge
from app.models.student import Student

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class SkillCount(BaseModel):
    skill: str
    count: int


class TelemetryResponse(BaseModel):
    bridge_status_counts: dict[str, int]
    top_requested_skills: list[SkillCount]


@router.get("/telemetry", response_model=TelemetryResponse)
async def get_telemetry(
    db: AsyncSession = Depends(get_db_session),
) -> TelemetryResponse:
    status_rows = (
        await db.execute(
            select(ChatBridge.status, func.count(ChatBridge.id)).group_by(
                ChatBridge.status
            )
        )
    ).all()
    status_counts = {status.value: 0 for status in BridgeStatus}
    for bridge_status, count in status_rows:
        status_key = getattr(bridge_status, "value", str(bridge_status))
        status_counts[status_key] = int(count)

    opted_in_tags = (
        await db.scalars(
            select(Student.tags).where(Student.matchmaking_opt_in.is_(True))
        )
    ).all()
    tag_counts: Counter[str] = Counter()
    for tags in opted_in_tags:
        # Count a normalized skill once per opted-in student.
        normalized_tags = {
            " ".join(str(tag).lower().split()) for tag in (tags or []) if str(tag).strip()
        }
        tag_counts.update(normalized_tags)

    top_skills = [
        SkillCount(skill=skill, count=count)
        for skill, count in sorted(
            tag_counts.items(), key=lambda item: (-item[1], item[0])
        )[:10]
    ]
    return TelemetryResponse(
        bridge_status_counts=status_counts,
        top_requested_skills=top_skills,
    )
