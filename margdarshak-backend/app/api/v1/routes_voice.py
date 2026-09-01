import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.call_session import CallFlowType, CallSession
from app.models.student import Student
from app.models.placement_drive import PlacementDrive
from app.models.ticket import Ticket, TicketStatus
from app.services.agora_service import (
    AgoraServiceError,
    generate_rtc_token,
    start_agent_session,
    stop_agent_session,
)
from app.services.conversation_orchestrator import (
    handle_conversation_turn,
    initialize_triage_session,
)

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
    agent: dict[str, object]


class TriageTurnRequest(BaseModel):
    transcript_chunk: str = Field(min_length=1)


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
        rtc_token = generate_rtc_token(payload.channel_name, payload.uid)
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
        )
        db.add(ticket)
        await db.flush()
        agent = await start_agent_session(payload.channel_name, payload.uid)
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
        agent=agent,
    )


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
    }
