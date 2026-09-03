import json
import re
import uuid
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.db.redis import get_redis_client
from app.db.session_factory import get_session_factory
from app.models.call_session import CallSession
from app.models.ticket import Ticket
from app.models.transcript import TranscriptSpeaker
from app.services.resource_diagnostic_service import (
    DiagnosticCriteria,
    extract_criteria,
    recommend,
)
from app.services.transcript_service import append_turn
from app.services.case_card_service import update_case_card

QUESTIONS = (
    ("skill", "Which skill do you want to learn—for example, Java DSA or System Design?"),
    ("pacing", "Do you want a short crash course or a long deep-dive?"),
    ("delivery", "Would you prefer a hands-on sheet or video, and must it be free or can it be paid?"),
)

LINK_REQUEST_PATTERN = re.compile(
    r"\b(?:link|url|resource)\b|\b(?:send|give|share|show|place|paste|attach)\b.*\blink\b",
    re.IGNORECASE,
)


def _state_key(session_id: uuid.UUID | str) -> str:
    return f"resource-diagnostic:session:{session_id}"


async def _student_id_for_session(session_id: uuid.UUID) -> uuid.UUID:
    async with get_session_factory()() as db:
        call_session = await db.get(CallSession, session_id)
    if call_session is None:
        raise ValueError(f"call session {session_id} does not exist")
    return call_session.student_id


async def _ticket_id_for_session(session_id: uuid.UUID) -> uuid.UUID:
    async with get_session_factory()() as db:
        ticket_id = await db.scalar(
            select(Ticket.id).where(Ticket.transcript_ref == str(session_id))
        )
    if ticket_id is None:
        raise ValueError(f"call session {session_id} has no associated ticket")
    return ticket_id


async def _load_state(session_id: uuid.UUID | str) -> dict[str, Any]:
    raw_state = await get_redis_client().get(_state_key(session_id))
    if raw_state is None:
        return {
            "flow_type": "resource_diagnostic",
            "transcript_history": [],
            "criteria": {"skill": None, "pacing": None, "format": None, "budget": None},
            "questions_asked": [],
            "complete": False,
            "recommendation": None,
        }
    return json.loads(raw_state)


async def _save_state(session_id: uuid.UUID | str, state: dict[str, Any]) -> None:
    await get_redis_client().set(
        _state_key(session_id),
        json.dumps(state),
        ex=get_settings().triage_session_ttl_seconds,
    )


async def handle_resource_turn(
    session_id: uuid.UUID | str, transcript_chunk: str
) -> dict[str, Any]:
    """Interpret one answer, ask at most three probes, then recommend."""

    chunk = transcript_chunk.strip()
    if not chunk:
        raise ValueError("transcript_chunk must not be empty")
    normalized_session_id = uuid.UUID(str(session_id))
    state = await _load_state(session_id)
    if state["complete"]:
        return {
            "flow_type": "resource_diagnostic",
            "complete": True,
            "criteria": state["criteria"],
            "recommendation": state["recommendation"],
        }

    await append_turn(normalized_session_id, TranscriptSpeaker.STUDENT, chunk)
    history = state["transcript_history"]
    history.append({"speaker": "student", "content": chunk})
    extracted = extract_criteria(history)
    criteria = state["criteria"]
    for key, value in extracted.items():
        if value is not None:
            criteria[key] = value

    # When the student explicitly asks for the link after naming a topic, do
    # not strand them in a preference loop. Use transparent, conservative
    # defaults for anything still missing; the recommender can relax them if
    # no exact resource exists.
    if criteria["skill"] and LINK_REQUEST_PATTERN.search(chunk):
        criteria["pacing"] = criteria["pacing"] or "short"
        criteria["format"] = criteria["format"] or "sheet"
        criteria["budget"] = criteria["budget"] or "free"
    ticket_id = await _ticket_id_for_session(normalized_session_id)
    await update_case_card(
        ticket_id,
        {
            "request_type": "learning_resource",
            "topic": criteria["skill"],
            "study_pace": criteria["pacing"],
            "study_style": criteria["format"],
            "budget": criteria["budget"],
        },
    )

    if all(criteria.values()):
        student_id = await _student_id_for_session(normalized_session_id)
        resource = await recommend(
            student_id, normalized_session_id, DiagnosticCriteria(**criteria)
        )
        recommendation = {
            "resource_id": str(resource.id),
            "title": resource.title,
            "url": resource.url,
            "skill": resource.skill_tag,
            "format": resource.format.value,
            "pacing": resource.pacing.value,
            "price_tier": resource.price_tier.value,
        }
        state["complete"] = True
        state["recommendation"] = recommendation
        await update_case_card(
            ticket_id,
            {"recommended_resource": resource.title, "resource_url": resource.url},
        )
        await _save_state(session_id, state)
        return {
            "flow_type": "resource_diagnostic",
            "complete": True,
            "criteria": criteria,
            "recommendation": recommendation,
        }

    question_key: str | None = None
    question: str | None = None
    for key, candidate in QUESTIONS:
        required_values = ("format", "budget") if key == "delivery" else (key,)
        if any(criteria[value] is None for value in required_values):
            question_key, question = key, candidate
            break

    if len(state["questions_asked"]) >= 3 or question is None:
        await _save_state(session_id, state)
        return {
            "flow_type": "resource_diagnostic",
            "complete": False,
            "next_action": "manual_clarification",
            "criteria": criteria,
            "message": "The diagnostic could not resolve all preferences in three questions.",
        }

    state["questions_asked"].append(question_key)
    history.append({"speaker": "agent", "content": question})
    await append_turn(normalized_session_id, TranscriptSpeaker.AGENT, question)
    await _save_state(session_id, state)
    return {
        "flow_type": "resource_diagnostic",
        "complete": False,
        "next_action": "ask_question",
        "question": question,
        "criteria": criteria,
        "questions_asked": len(state["questions_asked"]),
    }
