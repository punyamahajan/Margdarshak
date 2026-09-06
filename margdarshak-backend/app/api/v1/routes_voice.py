import re
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.call_session import CallFlowType, CallSession
from app.models.case_card import CaseCard
from app.models.resource import Resource, ResourceRecommendation
from app.models.student import Student
from app.models.placement_drive import PlacementDrive
from app.models.ticket import Ticket, TicketStatus
from app.services.case_card_service import CaseCardNotFoundError, get_case_card
from app.services.agora_service import (
    AgoraServiceError,
    generate_rtc_token,
    generate_rtc_rtm_token,
    start_agent_session,
    stop_agent_session,
)
from app.services.conversation_orchestrator import (
    handle_conversation_turn,
    initialize_triage_session,
)
from app.services.transcript_service import append_turn, get_transcript
from app.models.transcript import Transcript, TranscriptSpeaker

router = APIRouter(prefix="/voice", tags=["voice"])


class StartVoiceSessionRequest(BaseModel):
    student_id: uuid.UUID
    channel_name: str = Field(min_length=1, max_length=255)
    uid: int = Field(ge=2, le=2_147_483_646)


class StartVoiceSessionResponse(BaseModel):
    session_id: uuid.UUID
    ticket_id: uuid.UUID
    agora_app_id: str
    channel_name: str
    uid: int
    rtc_token: str
    rtm_token: str
    agent: dict[str, object]


class TriageTurnRequest(BaseModel):
    transcript_chunk: str = Field(min_length=1)


class TranscriptEventRequest(BaseModel):
    speaker: TranscriptSpeaker
    content: str = Field(min_length=1)
    is_final: bool = True


@router.post(
    "/session/start",
    response_model=StartVoiceSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_voice_session(
    payload: StartVoiceSessionRequest,
    db: AsyncSession = Depends(get_db_session),
) -> StartVoiceSessionResponse:
    try:
        rtc_token = generate_rtc_rtm_token(payload.channel_name, payload.uid)
        rtm_token = rtc_token
        student = await db.scalar(select(Student).where(Student.id == payload.student_id))
        if student is None:
            raise HTTPException(status_code=404, detail="student not found")

        call_session = CallSession(
            agora_channel_id=payload.channel_name,
            student_id=payload.student_id,
            flow_type=CallFlowType.TRIAGE,
        )
        db.add(call_session)
        await db.flush()
        ticket = Ticket(
            student_id=payload.student_id,
            issue_summary="",
            transcript_ref=str(call_session.id),
            confidence_score=0.0,
            status=TicketStatus.OPEN,
            escalated_to="",
            roll_number_snapshot=student.roll_number,
            similar_count=1,
        )
        db.add(ticket)
        await db.flush()
        db.add(
            CaseCard(
                ticket_id=ticket.id,
                structured_json={
                    "student_name": student.name,
                    "university": student.university,
                    "branch": student.branch,
                    "roll_number": student.roll_number,
                    "interests": student.tags,
                },
            )
        )
        previous_turns = (
            await db.scalars(
                select(Transcript)
                .join(CallSession, Transcript.call_session_id == CallSession.id)
                .where(
                    CallSession.student_id == payload.student_id,
                    CallSession.id != call_session.id,
                )
                .order_by(Transcript.timestamp.desc())
                .limit(12)
            )
        ).all()
        prior_context = "\n".join(
            f"{turn.speaker.value}: {turn.content}" for turn in reversed(previous_turns)
        )
        student_context = (
            f"Name: {student.name}; university: {student.university}; "
            f"branch: {student.branch}; roll number: {student.roll_number}; "
            f"interests: {', '.join(student.tags) or 'not recorded'}"
        )
        agent = await start_agent_session(
            payload.channel_name,
            payload.uid,
            student_context=student_context,
            prior_context=prior_context,
        )
        call_session.agora_agent_id = str(agent["agent_id"])
        await initialize_triage_session(call_session.id, ticket.id)
        await db.commit()
    except AgoraServiceError as exc:
        await db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception:
        await db.rollback()
        raise

    return StartVoiceSessionResponse(
        session_id=call_session.id,
        ticket_id=ticket.id,
        agora_app_id=get_settings().agora_app_id,
        channel_name=payload.channel_name,
        uid=payload.uid,
        rtc_token=rtc_token,
        rtm_token=rtm_token,
        agent=agent,
    )


@router.get("/session/{session_id}/transcript")
async def read_voice_transcript(session_id: uuid.UUID) -> list[dict[str, object]]:
    return await get_transcript(session_id)


@router.get("/session/{session_id}/summary")
async def read_voice_session_summary(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    session = await db.get(CallSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="call session not found")

    turns = await get_transcript(session_id)

    # Fetch associated ticket if any
    ticket = await db.scalar(
        select(Ticket).where(Ticket.transcript_ref == str(session_id))
    )
    case_card_data: dict[str, Any] | None = None
    if ticket is not None:
        try:
            case_card_data = await get_case_card(ticket.id)
        except CaseCardNotFoundError:
            case_card_data = None

    # Fetch associated resource recommendation if any
    rec_row = (
        await db.execute(
            select(ResourceRecommendation, Resource)
            .join(Resource, ResourceRecommendation.resource_id == Resource.id)
            .where(ResourceRecommendation.session_id == session_id)
        )
    ).first()

    url_pattern = re.compile(r"https?://[^\s<>\"'()]+", re.IGNORECASE)
    seen_urls: set[str] = set()
    links: list[dict[str, object]] = []

    # 1. From recommendations
    if rec_row is not None:
        rec, res = rec_row
        url = res.url.strip()
        if url and url not in seen_urls:
            seen_urls.add(url)
            links.append({
                "url": url,
                "title": res.title,
                "category": res.skill_tag if hasattr(res, "skill_tag") else "Learning Resource",
                "format": res.format.value if hasattr(res.format, "value") else str(res.format),
                "source": "resource_recommendation",
                "snippet": rec.reasoning_snapshot or f"Recommended for {res.skill_tag}",
            })

    # 2. From case card
    if case_card_data and isinstance(case_card_data, dict):
        resource_url = case_card_data.get("resource_url")
        if resource_url and isinstance(resource_url, str) and resource_url.strip() not in seen_urls:
            url = resource_url.strip()
            seen_urls.add(url)
            links.append({
                "url": url,
                "title": case_card_data.get("recommended_resource") or "Recommended Resource",
                "category": case_card_data.get("topic") or "Resource",
                "source": "case_card",
                "snippet": case_card_data.get("action_taken") or "Resource provided during triage",
            })

    # 3. From turns
    for turn in turns:
        content = turn.get("content", "")
        speaker = turn.get("speaker", "agent")
        matches = url_pattern.findall(content)
        for match in matches:
            cleaned_url = match.rstrip(".,;!?:")
            if cleaned_url and cleaned_url not in seen_urls:
                seen_urls.add(cleaned_url)
                parsed = urlparse(cleaned_url)
                title = parsed.netloc.replace("www.", "")
                if parsed.path and parsed.path != "/":
                    slug = parsed.path.strip("/").split("/")[-1].replace("-", " ").replace("_", " ").title()
                    if slug:
                        title = f"{slug} ({title})"
                links.append({
                    "url": cleaned_url,
                    "title": title,
                    "category": "Shared by Margdarshak" if speaker == "agent" else "Shared in Conversation",
                    "source": "agent_turn" if speaker == "agent" else "student_turn",
                    "snippet": content[:160] + ("…" if len(content) > 160 else ""),
                })

    student_turns = [t["content"] for t in turns if t.get("speaker") == "student"]
    agent_turns = [t["content"] for t in turns if t.get("speaker") == "agent"]

    topic = "Voice Guidance Session"
    if ticket and ticket.issue_summary:
        topic = ticket.issue_summary
    elif student_turns:
        first_q = student_turns[0].strip()
        topic = first_q[:60] + ("…" if len(first_q) > 60 else "")

    status_text = "Guidance Provided"
    if ticket:
        if ticket.status == TicketStatus.ESCALATED:
            status_text = f"Escalated to {ticket.escalated_to}"
        elif ticket.status == TicketStatus.RESOLVED:
            status_text = "Resolved by Margdarshak AI"
        else:
            status_text = "Case Logged"

    return {
        "session_id": str(session.id),
        "started_at": session.started_at.isoformat() if hasattr(session.started_at, "isoformat") else session.started_at,
        "ended_at": session.ended_at.isoformat() if hasattr(session.ended_at, "isoformat") else session.ended_at,
        "turns_count": len(turns),
        "topic": topic,
        "summary": {
            "topic": topic,
            "student_query": " ".join(student_turns) if student_turns else "No student speech recorded.",
            "ai_guidance": " ".join(agent_turns) if agent_turns else "Margdarshak listened to the student.",
            "status": status_text,
            "confidence_score": ticket.confidence_score if ticket else None,
            "escalated_to": ticket.escalated_to if ticket else None,
            "case_card": case_card_data,
        },
        "links": links,
        "recommendation": {
            "title": rec_row[1].title,
            "url": rec_row[1].url,
            "format": rec_row[1].format.value if hasattr(rec_row[1].format, "value") else str(rec_row[1].format),
            "pacing": rec_row[1].pacing.value if hasattr(rec_row[1].pacing, "value") else str(rec_row[1].pacing),
            "price_tier": rec_row[1].price_tier.value if hasattr(rec_row[1].price_tier, "value") else str(rec_row[1].price_tier),
            "reasoning": rec_row[0].reasoning_snapshot,
        } if rec_row else None,
        "turns": turns,
    }



@router.get("/history/{student_id}")
async def read_student_voice_history(
    student_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, object]]:
    sessions = (
        await db.scalars(
            select(CallSession)
            .where(CallSession.student_id == student_id)
            .order_by(CallSession.started_at.desc())
            .limit(10)
        )
    ).all()
    return [
        {
            "session_id": str(session.id),
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "turns": await get_transcript(session.id),
        }
        for session in sessions
    ]


@router.post("/session/{session_id}/transcript")
async def ingest_voice_transcript(
    session_id: uuid.UUID, payload: TranscriptEventRequest
) -> dict[str, object]:
    """Persist final Agora RTM transcript turns and update orchestration state."""

    if not payload.is_final:
        return {"accepted": False, "reason": "interim"}
    if payload.speaker == TranscriptSpeaker.STUDENT:
        result = await handle_conversation_turn(session_id, payload.content)
        return {"accepted": True, "orchestration": result}
    await append_turn(session_id, payload.speaker, payload.content)
    return {"accepted": True}


@router.post("/session/{session_id}/turn")
async def process_triage_turn(
    session_id: uuid.UUID, payload: TriageTurnRequest
) -> dict[str, object]:
    try:
        return await handle_conversation_turn(session_id, payload.transcript_chunk)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/session/{session_id}/end")
async def end_voice_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    call_session = await db.scalar(
        select(CallSession)
        .where(CallSession.id == session_id)
        .with_for_update()
    )
    if call_session is None:
        raise HTTPException(status_code=404, detail="call session not found")
    if call_session.agora_agent_id:
        try:
            await stop_agent_session(call_session.agora_agent_id)
            call_session.agora_agent_id = None
        except AgoraServiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    if call_session.ended_at is None:
        call_session.ended_at = datetime.now(timezone.utc)
        await db.commit()
    return {"session_id": call_session.id, "ended_at": call_session.ended_at}


@router.get("/session/{session_id}/status")
async def get_voice_session_status(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    call_session = await db.get(CallSession, session_id)
    if call_session is None:
        raise HTTPException(status_code=404, detail="call session not found")

    row = (
        await db.execute(
            select(Ticket, PlacementDrive)
            .outerjoin(PlacementDrive, PlacementDrive.id == Ticket.drive_id)
            .where(Ticket.transcript_ref == str(session_id))
            .order_by(Ticket.created_at.desc())
            .limit(1)
        )
    ).first()
    ticket, drive = row if row is not None else (None, None)
    escalated = ticket is not None and ticket.status == TicketStatus.ESCALATED
    return {
        "session_id": session_id,
        "ended_at": call_session.ended_at,
        "escalated": escalated,
        "poc_name": drive.poc_name if escalated and drive is not None else None,
        "handoff_status": (
            "queued_for_human_support" if escalated else None
        ),
    }
