import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.chat_bridge import BridgeStatus, ChatBridge
from app.services.matchmaker_service import (
    MatchmakerError,
    create_bridge,
    find_match,
    opt_in_student,
    request_reveal,
    request_voice_upgrade,
)

router = APIRouter(prefix="/matchmaker", tags=["matchmaker"])


class MatchRequest(BaseModel):
    student_id: uuid.UUID
    tags: list[str] = Field(default_factory=list)
    campus_responsibility: str | None = None
    criteria: dict[str, Any] = Field(default_factory=dict)


class AnonymousBridgeResponse(BaseModel):
    matched: bool
    bridge_id: uuid.UUID | None = None
    status: BridgeStatus | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None


class ConsentRequest(BaseModel):
    student_id: uuid.UUID


class RevealResponse(BaseModel):
    status: str
    linkedin_urls: list[str | None] | None = None


class VoiceUpgradeResponse(BaseModel):
    status: str
    channel_name: str | None = None
    rtc_tokens: list[str] | None = None


def _criteria_from_request(payload: MatchRequest) -> dict[str, Any]:
    criteria = dict(payload.criteria)
    existing_tags = criteria.get("tags", [])
    if not isinstance(existing_tags, list):
        existing_tags = []
    criteria["tags"] = [*existing_tags, *payload.tags]
    if payload.campus_responsibility:
        criteria["campus_responsibility"] = payload.campus_responsibility
    return criteria


@router.post(
    "/request",
    response_model=AnonymousBridgeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_match(payload: MatchRequest) -> AnonymousBridgeResponse:
    criteria = _criteria_from_request(payload)
    try:
        normalized_tags = await opt_in_student(payload.student_id, criteria)
        matched_student_id = await find_match(payload.student_id, criteria)
        if matched_student_id is None:
            return AnonymousBridgeResponse(matched=False)

        shared_description = ", ".join(sorted(normalized_tags))
        bridge = await create_bridge(
            payload.student_id,
            matched_student_id,
            f"Shared matchmaking criteria: {shared_description}",
        )
    except MatchmakerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AnonymousBridgeResponse(
        matched=True,
        bridge_id=bridge.id,
        status=bridge.status,
        created_at=bridge.created_at,
        expires_at=bridge.expires_at,
    )


@router.get("/bridge/{bridge_id}", response_model=AnonymousBridgeResponse)
async def get_bridge(
    bridge_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> AnonymousBridgeResponse:
    bridge = await db.get(ChatBridge, bridge_id)
    if bridge is None:
        raise HTTPException(status_code=404, detail="bridge not found")

    current_status = bridge.status
    if current_status == BridgeStatus.ACTIVE and bridge.expires_at <= datetime.now(
        timezone.utc
    ):
        current_status = BridgeStatus.EXPIRED

    return AnonymousBridgeResponse(
        matched=True,
        bridge_id=bridge.id,
        status=current_status,
        created_at=bridge.created_at,
        expires_at=bridge.expires_at,
    )


@router.post(
    "/bridge/{bridge_id}/reveal",
    response_model=RevealResponse,
    response_model_exclude_none=True,
)
async def reveal_identities(
    bridge_id: uuid.UUID, payload: ConsentRequest
) -> dict[str, Any]:
    try:
        return await request_reveal(bridge_id, payload.student_id)
    except MatchmakerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/bridge/{bridge_id}/upgrade-voice",
    response_model=VoiceUpgradeResponse,
    response_model_exclude_none=True,
)
async def upgrade_bridge_to_voice(
    bridge_id: uuid.UUID, payload: ConsentRequest
) -> dict[str, Any]:
    try:
        return await request_voice_upgrade(bridge_id, payload.student_id)
    except MatchmakerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
