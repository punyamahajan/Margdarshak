import uuid
from typing import Any

from sqlalchemy import func, select

from app.db.session_factory import get_session_factory
from app.models.call_session import CallSession
from app.models.transcript import Transcript, TranscriptSpeaker


class CallSessionNotFoundError(LookupError):
    pass


async def append_turn(
    call_session_id: uuid.UUID,
    speaker: TranscriptSpeaker | str,
    content: str,
) -> Transcript:
    """Append one turn, assigning an index safely for concurrent writers."""

    rendered_content = content.strip()
    if not rendered_content:
        raise ValueError("transcript content must not be empty")
    rendered_speaker = TranscriptSpeaker(speaker)

    async with get_session_factory()() as session:
        async with session.begin():
            locked_session_id = await session.scalar(
                select(CallSession.id)
                .where(CallSession.id == call_session_id)
                .with_for_update()
            )
            if locked_session_id is None:
                raise CallSessionNotFoundError(
                    f"call session {call_session_id} does not exist"
                )

            last_turn_index = await session.scalar(
                select(func.max(Transcript.turn_index)).where(
                    Transcript.call_session_id == call_session_id
                )
            )
            transcript = Transcript(
                call_session_id=call_session_id,
                turn_index=(last_turn_index if last_turn_index is not None else -1) + 1,
                speaker=rendered_speaker,
                content=rendered_content,
            )
            session.add(transcript)
            await session.flush()
            await session.refresh(transcript)

        return transcript


async def get_transcript(call_session_id: uuid.UUID) -> list[dict[str, Any]]:
    async with get_session_factory()() as session:
        turns = (
            await session.scalars(
                select(Transcript)
                .where(Transcript.call_session_id == call_session_id)
                .order_by(Transcript.turn_index)
            )
        ).all()

    return [
        {
            "id": str(turn.id),
            "call_session_id": str(turn.call_session_id),
            "turn_index": turn.turn_index,
            "speaker": turn.speaker.value,
            "content": turn.content,
            "timestamp": turn.timestamp,
        }
        for turn in turns
    ]


async def format_for_handoff(call_session_id: uuid.UUID) -> str:
    """Render recent conversation context for a concise human handoff."""

    turns = await get_transcript(call_session_id)
    if not turns:
        return "No conversation transcript is available yet."

    speaker_labels = {
        TranscriptSpeaker.STUDENT.value: "Student",
        TranscriptSpeaker.AGENT.value: "Agent",
        TranscriptSpeaker.HUMAN_COORDINATOR.value: "Coordinator",
    }
    lines = [
        f"{speaker_labels[turn['speaker']]}: {turn['content']}" for turn in turns
    ]
    selected_lines: list[str] = []
    selected_length = 0
    for line in reversed(lines):
        added_length = len(line) + (1 if selected_lines else 0)
        if selected_lines and selected_length + added_length > 1500:
            break
        selected_lines.append(line[:1500])
        selected_length += added_length
    return "\n".join(reversed(selected_lines))
