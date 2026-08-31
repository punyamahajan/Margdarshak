import asyncio
import uuid

from app.models.call_session import CallFlowType, CallSession
from app.models.student import Student
from app.models.ticket import Ticket, TicketStatus
from app.services import escalation_service


class AsyncContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeSession(AsyncContext):
    def __init__(self, ticket: Ticket, call_session: CallSession) -> None:
        self.ticket = ticket
        self.call_session = call_session

    def begin(self) -> AsyncContext:
        return AsyncContext()

    async def scalar(self, statement):
        return self.ticket

    async def get(self, model, identifier, **kwargs):
        return self.call_session


def test_trigger_escalation_only_reads_placement_drives(monkeypatch) -> None:
    student_id = uuid.uuid4()
    drive_id = uuid.uuid4()
    ticket_id = uuid.uuid4()
    session_id = uuid.uuid4()
    student = Student(
        id=student_id,
        roll_number="ROLL-42",
        name="Test Student",
        email="student@example.test",
        branch="CSE",
        phone="0000000000",
    )
    ticket = Ticket(
        id=ticket_id,
        student_id=student_id,
        drive_id=drive_id,
        issue_summary="Portal issue",
        transcript_ref="agora://test",
        confidence_score=0.5,
        status=TicketStatus.OPEN,
        escalated_to="",
        roll_number_snapshot="",
    )
    ticket.student = student
    call_session = CallSession(
        id=session_id,
        student_id=student_id,
        agora_channel_id="channel-1",
        flow_type=CallFlowType.TRIAGE,
    )
    fake_session = FakeSession(ticket, call_session)
    placement_drive_operations: list[str] = []

    async def fake_query_drive_policy(requested_drive_id):
        placement_drive_operations.append("select")
        assert requested_drive_id == drive_id
        return {"poc_contact": "poc@example.test"}

    async def fake_get_case_card(requested_ticket_id):
        assert requested_ticket_id == ticket_id
        return {"issue_summary": "Portal issue", "confidence_score": 0.5}

    async def fake_handover(channel_name, poc_contact, summary):
        return {"status": "handover_pending"}

    monkeypatch.setattr(
        escalation_service, "get_session_factory", lambda: lambda: fake_session
    )
    monkeypatch.setattr(
        escalation_service, "query_drive_policy", fake_query_drive_policy
    )
    monkeypatch.setattr(escalation_service, "get_case_card", fake_get_case_card)
    monkeypatch.setattr(escalation_service, "handover_to_human", fake_handover)

    result = asyncio.run(escalation_service.trigger_escalation(session_id, ticket_id))

    assert placement_drive_operations == ["select"]
    assert ticket.status is TicketStatus.ESCALATED
    assert ticket.escalated_to == "poc@example.test"
    assert ticket.roll_number_snapshot == "ROLL-42"
    assert result["triggered"] is True
