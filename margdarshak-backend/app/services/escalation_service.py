import json
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.readonly_gateway import query_drive_policy
from app.db.session_factory import get_session_factory
from app.models.call_session import CallFlowType, CallSession
from app.models.ticket import Ticket, TicketStatus
from app.services.agora_service import handover_to_human
from app.services.case_card_service import get_case_card
from app.services.transcript_service import format_for_handoff

logger = logging.getLogger(__name__)


class EscalationError(RuntimeError):
    pass


async def format_case_summary(
    case_card_json: dict[str, Any], call_session_id: uuid.UUID
) -> str:
    """Format the most useful case-card fields into a concise handoff brief."""

    labels = (
        ("classification", "Type"),
        ("issue_summary", "Issue"),
        ("confidence_score", "Confidence"),
        ("time_sensitive", "Time sensitive"),
        ("drive_id", "Drive"),
        ("last_transcript_chunk", "Latest statement"),
    )
    lines: list[str] = []
    for key, label in labels:
        value = case_card_json.get(key)
        if value is not None and value != "":
            rendered = value if isinstance(value, str) else json.dumps(value)
            lines.append(f"{label}: {rendered}")

    transcript = await format_for_handoff(call_session_id)
    if not lines:
        lines.append("No structured case details are available yet.")
    lines.extend(("Conversation:", transcript))
    return "\n".join(lines)[:3500]


async def trigger_escalation(
    session_id: uuid.UUID, ticket_id: uuid.UUID
) -> dict[str, Any]:
    """Escalate a triage ticket and initiate an Agora human handoff."""

    case_card = await get_case_card(ticket_id)

    async with get_session_factory()() as db:
        async with db.begin():
            ticket = await db.scalar(
                select(Ticket)
                .options(selectinload(Ticket.student))
                .where(Ticket.id == ticket_id)
                .with_for_update()
            )
            if ticket is None:
                raise EscalationError(f"ticket {ticket_id} does not exist")

            call_session = await db.get(CallSession, session_id, with_for_update=True)
            if call_session is None:
                raise EscalationError(f"call session {session_id} does not exist")
            if call_session.student_id != ticket.student_id:
                raise EscalationError("call session and ticket belong to different students")

            if ticket.drive_id is None and case_card.get("drive_id"):
                ticket.drive_id = uuid.UUID(str(case_card["drive_id"]))
            if ticket.drive_id is None:
                # An urgent student should not be blocked because they do not know
                # an internal drive UUID. Route it to the demo placement desk.
                poc_contact = "demo-placement-support-desk"
            else:
                # Placement-drive access is deliberately isolated behind the SELECT-only gateway.
                drive = await query_drive_policy(ticket.drive_id)
                poc_contact = str(drive.get("poc_contact", "")).strip()
                if not poc_contact:
                    poc_contact = "demo-placement-support-desk"

            ticket.status = TicketStatus.ESCALATED
            ticket.escalated_to = poc_contact
            ticket.roll_number_snapshot = ticket.student.roll_number

            summary = await format_case_summary(case_card, session_id)
            handover = await handover_to_human(
                call_session.agora_channel_id, poc_contact, summary
            )

            # No human-handoff enum exists; this remains a triage flow.
            call_session.flow_type = CallFlowType.TRIAGE

    logger.info(
        "placement_triage_handover",
        extra={
            "session_id": str(session_id),
            "ticket_id": str(ticket_id),
            "drive_id": str(ticket.drive_id),
            "poc_contact": poc_contact,
            "agora_channel_id": call_session.agora_channel_id,
        },
    )
    return {
        "triggered": True,
        "session_id": str(session_id),
        "ticket_id": str(ticket_id),
        "escalated_to": poc_contact,
        "handover": handover,
    }
