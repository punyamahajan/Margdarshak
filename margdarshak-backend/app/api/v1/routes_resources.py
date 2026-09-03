import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.call_session import CallSession
from app.models.resource import Resource, ResourceRecommendation
from app.models.ticket import Ticket
from app.models.transcript import Transcript, TranscriptSpeaker
from app.services.case_card_service import update_case_card
from app.services.resource_diagnostic_service import extract_criteria, recommend

router = APIRouter(prefix="/resources", tags=["resources"])


def _serialize_recommendation(
    recommendation: ResourceRecommendation, resource: Resource
) -> dict[str, object]:
    return {
        "recommendation_id": recommendation.id,
        "student_id": recommendation.student_id,
        "session_id": recommendation.session_id,
        "reasoning_snapshot": recommendation.reasoning_snapshot,
        "created_at": recommendation.created_at,
        "resource": {
            "id": resource.id,
            "skill_tag": resource.skill_tag,
            "title": resource.title,
            "url": resource.url,
            "format": resource.format.value,
            "pacing": resource.pacing.value,
            "price_tier": resource.price_tier.value,
        },
    }


async def _recommendation_row(session_id: uuid.UUID, db: AsyncSession):
    return (
        await db.execute(
            select(ResourceRecommendation, Resource)
            .join(Resource, Resource.id == ResourceRecommendation.resource_id)
            .where(ResourceRecommendation.session_id == session_id)
            .order_by(ResourceRecommendation.created_at.desc())
            .limit(1)
        )
    ).first()


@router.get("/recommendations/{session_id}")
async def get_resource_recommendation(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    row = await _recommendation_row(session_id, db)
    if row is None:
        raise HTTPException(status_code=404, detail="resource recommendation not found")

    return _serialize_recommendation(*row)


@router.post("/recommendations/{session_id}/ensure")
async def ensure_resource_recommendation(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """Recover a missing link from persisted voice turns, idempotently."""

    existing = await _recommendation_row(session_id, db)
    if existing is not None:
        _, existing_resource = existing
        serialized = _serialize_recommendation(*existing)
        resource_fields = {
            "request_type": "learning_resource",
            "topic": existing_resource.skill_tag,
            "recommended_resource": existing_resource.title,
            "resource_url": existing_resource.url,
        }
        ticket_id = await db.scalar(
            select(Ticket.id).where(Ticket.transcript_ref == str(session_id))
        )
        await db.rollback()
        if ticket_id is not None:
            await update_case_card(ticket_id, resource_fields)
        return serialized

    call_session = await db.get(CallSession, session_id)
    if call_session is None:
        raise HTTPException(status_code=404, detail="call session not found")
    turns = (
        await db.scalars(
            select(Transcript)
            .where(
                Transcript.call_session_id == session_id,
                Transcript.speaker == TranscriptSpeaker.STUDENT,
            )
            .order_by(Transcript.turn_index)
        )
    ).all()
    history = [{"speaker": "student", "content": turn.content} for turn in turns]
    criteria = extract_criteria(history)
    combined = " ".join(turn.content.lower() for turn in turns)
    link_requested = any(word in combined for word in ("link", "url", "resource"))
    if criteria["skill"] is None or not link_requested:
        raise HTTPException(
            status_code=404,
            detail="the transcript does not yet contain a topic and link request",
        )

    criteria["pacing"] = criteria["pacing"] or "short"
    criteria["format"] = criteria["format"] or "sheet"
    criteria["budget"] = criteria["budget"] or "free"
    resource = await recommend(call_session.student_id, session_id, criteria)
    # `recommend` commits through the service's own session. End this request's
    # older read transaction so the newly committed row is visible and no
    # connection state is retained while the case card is updated separately.
    await db.rollback()
    ticket_id = await db.scalar(
        select(Ticket.id).where(Ticket.transcript_ref == str(session_id))
    )
    if ticket_id is not None:
        await update_case_card(
            ticket_id,
            {
                "request_type": "learning_resource",
                "topic": criteria["skill"],
                "study_pace": criteria["pacing"],
                "study_style": criteria["format"],
                "budget": criteria["budget"],
                "recommended_resource": resource.title,
                "resource_url": resource.url,
            },
        )

    await db.rollback()
    created = await _recommendation_row(session_id, db)
    if created is None:
        raise HTTPException(status_code=500, detail="recommendation was not persisted")
    return _serialize_recommendation(*created)
