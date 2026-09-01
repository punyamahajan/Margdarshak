import asyncio
import uuid

from app.services import transcript_service


def test_format_for_handoff_orders_and_labels_turns(monkeypatch) -> None:
    session_id = uuid.uuid4()

    async def fake_get_transcript(requested_session_id):
        assert requested_session_id == session_id
        return [
            {"speaker": "student", "content": "My application link is broken."},
            {"speaker": "agent", "content": "I will escalate this now."},
            {
                "speaker": "human_coordinator",
                "content": "I can help before the deadline.",
            },
        ]

    monkeypatch.setattr(transcript_service, "get_transcript", fake_get_transcript)

    result = asyncio.run(transcript_service.format_for_handoff(session_id))

    assert result.splitlines() == [
        "Student: My application link is broken.",
        "Agent: I will escalate this now.",
        "Coordinator: I can help before the deadline.",
    ]


def test_format_for_handoff_handles_empty_transcript(monkeypatch) -> None:
    async def fake_get_transcript(_session_id):
        return []

    monkeypatch.setattr(transcript_service, "get_transcript", fake_get_transcript)

    result = asyncio.run(transcript_service.format_for_handoff(uuid.uuid4()))

    assert result == "No conversation transcript is available yet."
