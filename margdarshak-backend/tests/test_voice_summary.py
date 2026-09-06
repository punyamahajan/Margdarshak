"""Tests for GET /api/v1/voice/session/{session_id}/summary."""

import uuid
import pytest
import httpx

from app.main import app
from app.db.session_factory import get_session_factory
from app.models.student import Student
from app.models.call_session import CallSession, CallFlowType
from app.models.transcript import Transcript, TranscriptSpeaker
from app.models.ticket import Ticket, TicketStatus


@pytest.mark.anyio
async def test_voice_session_summary_and_extracted_links():
    session_id = uuid.uuid4()
    student_id = uuid.uuid4()

    async with get_session_factory()() as session:
        # Create student
        student = Student(
            id=student_id,
            name="Aarav Gupta",
            roll_number=f"ROLL-{uuid.uuid4().hex[:6]}",
            email=f"aarav_{uuid.uuid4().hex[:6]}@demo.edu",
            branch="Computer Science",
            university="IIT Delhi",
            phone="+91 9999999999",
        )
        session.add(student)

        # Create call session
        call_session = CallSession(
            id=session_id,
            student_id=student_id,
            agora_channel_id=f"channel-{uuid.uuid4().hex[:8]}",
            flow_type=CallFlowType.RESOURCE_DIAGNOSTIC,
        )
        session.add(call_session)

        # Create turns with links
        turn1 = Transcript(
            call_session_id=session_id,
            turn_index=0,
            speaker=TranscriptSpeaker.STUDENT,
            content="Can you recommend good DSA resources and sheets for campus interviews?",
        )
        turn2 = Transcript(
            call_session_id=session_id,
            turn_index=1,
            speaker=TranscriptSpeaker.AGENT,
            content="I strongly recommend following the Striver SDE sheet at https://takeuforward.org/strivers-a2z-dsa-course/ and practicing on https://leetcode.com.",
        )
        session.add_all([turn1, turn2])

        # Create ticket
        ticket = Ticket(
            student_id=student_id,
            issue_summary="Recommended DSA resources and Striver sheet",
            transcript_ref=str(session_id),
            confidence_score=0.92,
            status=TicketStatus.RESOLVED,
            escalated_to="none",
            roll_number_snapshot=student.roll_number,
        )
        session.add(ticket)
        await session.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/voice/session/{session_id}/summary")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert data["session_id"] == str(session_id)
        assert data["turns_count"] == 2
        assert "summary" in data
        assert "topic" in data["summary"]
        assert "Resolved" in data["summary"]["status"]
        assert len(data["links"]) == 2

        urls = [link["url"] for link in data["links"]]
        assert "https://takeuforward.org/strivers-a2z-dsa-course/" in urls
        assert "https://leetcode.com" in urls

        # Test non-existent session
        bad_id = uuid.uuid4()
        bad_resp = await client.get(f"/api/v1/voice/session/{bad_id}/summary")
        assert bad_resp.status_code == 404
