import json
import re
import uuid
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.db.redis import get_redis_client
from app.db.readonly_gateway import query_drive_policy
from app.db.session_factory import get_session_factory
from app.models.call_session import CallFlowType, CallSession
from app.models.transcript import TranscriptSpeaker
from app.services.case_card_service import update_case_card
from app.services.confidence_engine import (
    CONFIDENCE_THRESHOLD,
    is_time_sensitive_grievance,
    score_confidence,
)
from app.services.escalation_service import trigger_escalation
from app.services.resource_diagnostic_orchestrator import handle_resource_turn
from app.services.transcript_service import append_turn

POLICY_TERMS = {
    "policy",
    "eligible",
    "eligibility",
    "criteria",
    "package",
    "salary",
    "bond",
    "deadline",
    "company",
    "drive",
}
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
RESOURCE_INTENT_PATTERN = re.compile(
    r"\b(resource|course|tutorial|learn|study|recommend|dsa|dbms|database|"
    r"operating system|system design|web development|frontend)\b",
    re.IGNORECASE,
)


def _state_key(session_id: uuid.UUID | str) -> str:
    return f"triage:session:{session_id}"


async def initialize_triage_session(
    session_id: uuid.UUID | str, ticket_id: uuid.UUID
) -> None:
    state = {
        "flow_type": "undetermined",
        "transcript_chunks": [],
        "issue_summary": "",
        "classification": None,
        "drive_id": None,
        "ticket_id": str(ticket_id),
    }
    await _save_state(session_id, state)


async def _load_state(session_id: uuid.UUID | str) -> dict[str, Any]:
    raw_state = await get_redis_client().get(_state_key(session_id))
    if raw_state is None:
        return {
            "flow_type": "undetermined",
            "transcript_chunks": [],
            "issue_summary": "",
            "classification": None,
            "drive_id": None,
            "ticket_id": None,
        }
    return json.loads(raw_state)


async def _save_state(session_id: uuid.UUID | str, state: dict[str, Any]) -> None:
    await get_redis_client().set(
        _state_key(session_id),
        json.dumps(state),
        ex=get_settings().triage_session_ttl_seconds,
    )


async def _set_call_flow(session_id: uuid.UUID, flow_type: CallFlowType) -> None:
    async with get_session_factory()() as db:
        async with db.begin():
            call_session = await db.scalar(
                select(CallSession).where(CallSession.id == session_id).with_for_update()
            )
            if call_session is None:
                raise ValueError(f"call session {session_id} does not exist")
            call_session.flow_type = flow_type


async def handle_conversation_turn(
    session_id: uuid.UUID | str, transcript_chunk: str
) -> dict[str, Any]:
    """Select a flow from initial intent, then keep that route for the call."""

    chunk = transcript_chunk.strip()
    if not chunk:
        raise ValueError("transcript_chunk must not be empty")
    state = await _load_state(session_id)
    flow_type = state.get("flow_type", "undetermined")
    if flow_type == "undetermined":
        # TODO: Replace this keyword router with a structured intent classifier.
        flow_type = (
            "resource_diagnostic"
            if RESOURCE_INTENT_PATTERN.search(chunk)
            else "triage"
        )
        state["flow_type"] = flow_type
        await _save_state(session_id, state)
        await _set_call_flow(
            uuid.UUID(str(session_id)),
            CallFlowType.RESOURCE_DIAGNOSTIC
            if flow_type == "resource_diagnostic"
            else CallFlowType.TRIAGE,
        )

    if flow_type == "resource_diagnostic":
        return await handle_resource_turn(session_id, chunk)
    return await handle_triage_turn(session_id, chunk)


async def handle_triage_turn(
    session_id: uuid.UUID | str, transcript_chunk: str
) -> dict[str, Any]:
    """Classify and route one transcript turn while retaining Redis state."""

    chunk = transcript_chunk.strip()
    if not chunk:
        raise ValueError("transcript_chunk must not be empty")

    normalized_session_id = uuid.UUID(str(session_id))
    await append_turn(normalized_session_id, TranscriptSpeaker.STUDENT, chunk)

    state = await _load_state(session_id)
    chunks = state.setdefault("transcript_chunks", [])
    chunks.append(chunk)
    state["issue_summary"] = " ".join(chunks)

    drive_match = UUID_PATTERN.search(chunk)
    if drive_match:
        state["drive_id"] = drive_match.group(0)

    normalized_words = set(re.findall(r"[a-z]+", chunk.lower()))
    is_policy_question = bool(normalized_words.intersection(POLICY_TERMS))

    if is_policy_question:
        state["classification"] = "policy_question"
        drive_id = state.get("drive_id")
        if drive_id is None:
            action: dict[str, Any] = {
                "next_action": "request_drive_id",
                "classification": "policy_question",
                "message": "A placement drive ID is needed to retrieve its policy.",
            }
        else:
            policy = await query_drive_policy(uuid.UUID(drive_id))
            action = {
                "next_action": "answer_from_drive_policy",
                "classification": "policy_question",
                "policy": policy,
            }
    else:
        state["classification"] = "grievance"
        # TODO(next chunk): persist/escalate a ticket and build its case card.
        action = {
            "next_action": "escalate_grievance",
            "classification": "grievance",
            "message": "The grievance is ready for escalation handling.",
        }

    action["issue_summary"] = state["issue_summary"]
    action["drive_id"] = state.get("drive_id")
    confidence = score_confidence(action)
    urgent = (
        action["classification"] == "grievance"
        and is_time_sensitive_grievance(chunk)
    )
    action["confidence_score"] = confidence
    action["time_sensitive"] = urgent

    ticket_id_value = state.get("ticket_id")
    if ticket_id_value is None:
        raise ValueError(f"triage session {session_id} has no associated ticket")
    ticket_id = uuid.UUID(ticket_id_value)

    await update_case_card(
        ticket_id,
        {
            "classification": action["classification"],
            "issue_summary": state["issue_summary"],
            "drive_id": state.get("drive_id"),
            "confidence_score": confidence,
            "time_sensitive": urgent,
            "last_transcript_chunk": chunk,
            "policy": action.get("policy"),
        },
    )

    escalation_reasons: list[str] = []
    if confidence < CONFIDENCE_THRESHOLD:
        escalation_reasons.append("low_confidence")
    if urgent:
        escalation_reasons.append("time_sensitive_grievance")

    if escalation_reasons:
        action["escalation"] = await trigger_escalation(
            normalized_session_id, ticket_id
        )

    state["confidence_score"] = confidence
    await _save_state(session_id, state)
    return action
