import json
import re
import uuid
from typing import Any

from app.core.config import get_settings
from app.db.redis import get_redis_client
from app.db.readonly_gateway import query_drive_policy
from app.services.case_card_service import update_case_card
from app.services.confidence_engine import (
    CONFIDENCE_THRESHOLD,
    is_time_sensitive_grievance,
    score_confidence,
)
from app.services.escalation_service import trigger_escalation

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


def _state_key(session_id: uuid.UUID | str) -> str:
    return f"triage:session:{session_id}"


async def initialize_triage_session(
    session_id: uuid.UUID | str, ticket_id: uuid.UUID
) -> None:
    state = {
        "flow_type": "triage",
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
            "flow_type": "triage",
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


async def handle_triage_turn(
    session_id: uuid.UUID | str, transcript_chunk: str
) -> dict[str, Any]:
    """Classify and route one transcript turn while retaining Redis state."""

    chunk = transcript_chunk.strip()
    if not chunk:
        raise ValueError("transcript_chunk must not be empty")

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
            uuid.UUID(str(session_id)), ticket_id
        )

    state["confidence_score"] = confidence
    await _save_state(session_id, state)
    return action
