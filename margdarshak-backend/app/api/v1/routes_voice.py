import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.call_session import CallFlowType, CallSession
from app.models.student import Student
from app.models.ticket import Ticket, TicketStatus
from app.services.agora_service import (
    AgoraServiceError,
    generate_rtc_token,
    start_agent_session,
)
from app.services.conversation_orchestrator import (
    handle_triage_turn,
    initialize_triage_session,
)

router = APIRouter(prefix="/voice", tags=["voice"])


class StartVoiceSessionRequest(BaseModel):
    student_id: uuid.UUID
    channel_name: str = Field(min_length=1, max_length=255)
    uid: int = Field(ge=0)


class StartVoiceSessionResponse(BaseModel):
    session_id: uuid.UUID
    ticket_id: uuid.UUID
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
        ticket = Ticket(
            student_id=payload.student_id,
            issue_summary="",
            transcript_ref=f"agora://{payload.channel_name}",
            confidence_score=0.0,
            status=TicketStatus.OPEN,
            escalated_to="",
            roll_number_snapshot=student.roll_number,
        )
        db.add_all([call_session, ticket])
        await db.flush()
        agent = await start_agent_session(payload.channel_name)
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
        return await handle_triage_turn(session_id, payload.transcript_chunk)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
