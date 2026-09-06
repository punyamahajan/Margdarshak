"""Agentic query deduplication and routing for placement grievances.

Uses Gemini (preferred) then OpenAI. Falls back to lexical similarity only if
both LLM providers fail.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from sqlalchemy import or_, select

from app.core.config import get_settings
from app.db.session_factory import get_session_factory
from app.models.call_session import CallSession
from app.models.ticket import Ticket, TicketStatus
from app.services.agora_service import (
    AgoraServiceError,
    notify_coordinator,
    speak_to_student,
)
from app.services.case_card_service import update_case_card
from app.services.escalation_service import trigger_escalation

logger = logging.getLogger(__name__)

DecisionKind = Literal["grouped", "escalated", "skipped", "collecting"]
CONNECTING_MESSAGE = "Connecting to coordinator."

STOPWORDS = {
    "a", "an", "and", "are", "for", "from", "have", "i", "in", "is", "it",
    "me", "my", "of", "on", "or", "please", "the", "to", "with",
}

ACK_PATTERN = re.compile(
    r"^\s*(yes|yeah|yep|yup|no|nope|ok|okay|sure|thanks|thank you|"
    r"hi|hello|hey|urgent|it is|it is urgent|yes it is)\s*[.!]?\s*$",
    re.IGNORECASE,
)
PLACEMENT_PATTERN = re.compile(
    r"\b(placement|drive|company|interview|job|application|apply|portal|"
    r"assessment|oa|deadline|offer|resume|document|eligible|eligibility|"
    r"tcs|amazon|infosys|wipro|accenture|google|microsoft|deloitte)\b",
    re.IGNORECASE,
)
ISSUE_PATTERN = re.compile(
    r"\b(not working|failed|failing|rejected|reject|error|issue|problem|"
    r"unable|cannot|can't|won't|expired|blocked|missing|stuck|broken|"
    r"upload|login|submit|open|reopen|access)\b",
    re.IGNORECASE,
)


@dataclass
class RoutingDecision:
    kind: DecisionKind
    student_message: str
    ticket_id: uuid.UUID
    parent_ticket_id: uuid.UUID | None = None
    similar_count: int = 1
    matched_summary: str | None = None
    llm_provider: str | None = None
    routing_score: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "student_message": self.student_message,
            "ticket_id": str(self.ticket_id),
            "parent_ticket_id": (
                str(self.parent_ticket_id) if self.parent_ticket_id else None
            ),
            "similar_count": self.similar_count,
            "matched_summary": self.matched_summary,
            "llm_provider": self.llm_provider,
            "routing_score": self.routing_score,
        }


def is_routable_query(text: str) -> bool:
    """Route once the student has described a concrete support issue."""

    query = " ".join(text.split()).strip()
    if len(query) < 18 or ACK_PATTERN.match(query):
        return False
    has_placement = bool(PLACEMENT_PATTERN.search(query))
    has_issue = bool(ISSUE_PATTERN.search(query))
    if has_placement and has_issue:
        return True
    # Support-chat style: a clear placement statement with enough detail.
    if has_placement and len(query) >= 35:
        return True
    if has_issue and len(query) >= 45:
        return True
    return False


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def _lexical_similarity(left: str, right: str) -> float:
    left_tokens = _tokenize(left)
    right_tokens = _tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = left_tokens.intersection(right_tokens)
    return len(overlap) / max(len(left_tokens.union(right_tokens)), 1)


def _extract_json(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None


def _similarity_prompt(query: str, candidates: list[dict[str, str]]) -> str:
    numbered = "\n".join(
        f"{index + 1}. id={item['id']} summary={item['summary']}"
        for index, item in enumerate(candidates)
    )
    return (
        "You route campus placement support tickets.\n"
        "Decide whether the NEW QUERY is semantically the same issue as one of the "
        "EXISTING OPEN TICKETS (same company/drive and same blocker).\n"
        "Reply with JSON only:\n"
        '{"match": true|false, "ticket_id": "<uuid or null>", "score": 0.0-1.0, '
        '"reason": "short"}\n'
        "Set match=true only when score >= 0.75.\n\n"
        f"NEW QUERY:\n{query}\n\nEXISTING OPEN TICKETS:\n{numbered or '(none)'}"
    )


async def _gemini_similarity(
    query: str, candidates: list[dict[str, str]], api_key: str, model: str
) -> dict[str, Any] | None:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    body = {
        "contents": [{"parts": [{"text": _similarity_prompt(query, candidates)}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    async with httpx.AsyncClient(timeout=25.0) as client:
        response = await client.post(url, json=body)
        if response.status_code >= 400:
            logger.warning(
                "query_routing_gemini_http_error status=%s body=%s",
                response.status_code,
                response.text[:300],
            )
            response.raise_for_status()
        payload = response.json()
    text = (
        payload.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
    )
    return _extract_json(text)


async def _openai_similarity(
    query: str, candidates: list[dict[str, str]], api_key: str, model: str
) -> dict[str, Any] | None:
    async with httpx.AsyncClient(timeout=25.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a careful placement-ticket routing agent.",
                    },
                    {"role": "user", "content": _similarity_prompt(query, candidates)},
                ],
            },
        )
        if response.status_code >= 400:
            logger.warning(
                "query_routing_openai_http_error status=%s body=%s",
                response.status_code,
                response.text[:300],
            )
            response.raise_for_status()
        payload = response.json()
    text = payload["choices"][0]["message"]["content"]
    return _extract_json(text)


async def _call_llm_similarity(
    query: str, candidates: list[dict[str, str]]
) -> tuple[dict[str, Any] | None, str | None]:
    """Try Gemini, then OpenAI. Returns (result, provider_name)."""

    settings = get_settings()
    provider = settings.llm_provider.strip().lower()
    gemini_key = settings.gemini_api_key.get_secret_value().strip()
    openai_key = settings.openai_api_key.get_secret_value().strip()
    gemini_model = settings.gemini_model.strip() or "gemini-flash-latest"
    openai_model = settings.openai_model.strip() or "gpt-4o-mini"

    order: list[str] = []
    if provider in {"auto", "gemini"} and gemini_key:
        order.append("gemini")
    if provider in {"auto", "openai", "gpt"} and openai_key:
        order.append("openai")
    if provider == "gemini" and openai_key and "openai" not in order:
        order.append("openai")
    if provider in {"openai", "gpt"} and gemini_key and "gemini" not in order:
        order.append("gemini")

    for name in order:
        try:
            if name == "gemini":
                result = await _gemini_similarity(
                    query, candidates, gemini_key, gemini_model
                )
            else:
                result = await _openai_similarity(
                    query, candidates, openai_key, openai_model
                )
            if result is not None:
                logger.info("query_routing_llm_ok provider=%s", name)
                return result, name
        except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            logger.warning(
                "query_routing_llm_failed provider=%s error=%s", name, exc
            )
    return None, None


async def find_similar_ticket(
    query: str, candidates: list[Ticket]
) -> tuple[Ticket | None, float, str | None]:
    """Return the best matching open root ticket, if any."""

    if not query.strip() or not candidates:
        return None, 0.0, None

    settings = get_settings()
    threshold = settings.query_similarity_threshold
    candidate_payload = [
        {"id": str(ticket.id), "summary": ticket.issue_summary.strip()}
        for ticket in candidates
        if ticket.issue_summary.strip()
    ]
    if not candidate_payload:
        return None, 0.0, None

    by_id = {str(ticket.id): ticket for ticket in candidates}
    llm_result, provider = await _call_llm_similarity(query, candidate_payload)

    if llm_result and llm_result.get("match"):
        ticket_id = str(llm_result.get("ticket_id") or "")
        score = float(llm_result.get("score") or 0.0)
        matched = by_id.get(ticket_id)
        if matched is not None and score >= min(threshold, 0.75):
            return matched, score, provider

    best_ticket: Ticket | None = None
    best_score = 0.0
    for ticket in candidates:
        score = _lexical_similarity(query, ticket.issue_summary)
        if score > best_score:
            best_ticket = ticket
            best_score = score
    # Lexical fallback is stricter so weak overlaps do not false-group.
    lexical_threshold = max(threshold, 0.55)
    if best_ticket is not None and best_score >= lexical_threshold:
        return best_ticket, best_score, provider or "lexical"
    return None, best_score, provider or "lexical"


async def _load_open_root_tickets(exclude_ticket_id: uuid.UUID) -> list[Ticket]:
    async with get_session_factory()() as db:
        tickets = (
            await db.scalars(
                select(Ticket)
                .where(
                    Ticket.id != exclude_ticket_id,
                    Ticket.parent_ticket_id.is_(None),
                    Ticket.issue_summary != "",
                    or_(
                        Ticket.status == TicketStatus.OPEN,
                        Ticket.status == TicketStatus.ESCALATED,
                    ),
                )
                .order_by(Ticket.created_at.desc())
                .limit(40)
            )
        ).all()
        return list(tickets)


async def _group_under_parent(
    ticket_id: uuid.UUID, parent_ticket_id: uuid.UUID, issue_summary: str
) -> dict[str, Any]:
    async with get_session_factory()() as db:
        async with db.begin():
            ticket = await db.scalar(
                select(Ticket).where(Ticket.id == ticket_id).with_for_update()
            )
            parent = await db.scalar(
                select(Ticket).where(Ticket.id == parent_ticket_id).with_for_update()
            )
            if ticket is None or parent is None:
                raise ValueError("ticket or parent ticket not found for grouping")
            root = parent
            while root.parent_ticket_id is not None:
                next_parent = await db.get(Ticket, root.parent_ticket_id)
                if next_parent is None:
                    break
                root = next_parent
            if root.id != parent.id:
                parent = await db.scalar(
                    select(Ticket).where(Ticket.id == root.id).with_for_update()
                )
                if parent is None:
                    raise ValueError("root parent ticket not found for grouping")

            ticket.issue_summary = issue_summary
            ticket.parent_ticket_id = parent.id
            ticket.status = parent.status
            ticket.escalated_to = parent.escalated_to
            parent.similar_count = int(parent.similar_count or 1) + 1
            await db.flush()
            return {
                "parent_id": parent.id,
                "parent_summary": parent.issue_summary,
                "parent_escalated_to": parent.escalated_to,
                "similar_count": int(parent.similar_count),
            }


async def _mark_ticket_summary(
    ticket_id: uuid.UUID, issue_summary: str, confidence_score: float
) -> None:
    async with get_session_factory()() as db:
        async with db.begin():
            ticket = await db.scalar(
                select(Ticket).where(Ticket.id == ticket_id).with_for_update()
            )
            if ticket is None:
                raise ValueError(f"ticket {ticket_id} does not exist")
            ticket.issue_summary = issue_summary
            ticket.confidence_score = confidence_score


async def _agent_channel_context(
    session_id: uuid.UUID,
) -> tuple[str | None, str]:
    async with get_session_factory()() as db:
        call_session = await db.get(CallSession, session_id)
        if call_session is None:
            return None, ""
        return call_session.agora_agent_id, call_session.agora_channel_id


async def _speak(agent_id: str | None, message: str) -> None:
    if not agent_id:
        return
    try:
        await speak_to_student(agent_id, message)
    except AgoraServiceError as exc:
        logger.warning("agora_speak_failed error=%s", exc)


async def route_student_query(
    session_id: uuid.UUID,
    ticket_id: uuid.UUID,
    query_text: str,
    *,
    confidence_score: float = 0.0,
    force: bool = False,
) -> RoutingDecision:
    """Deduplicate a student query or escalate it as a new coordinator ticket."""

    query = " ".join(query_text.split()).strip()
    if not force and not is_routable_query(query):
        await _mark_ticket_summary(ticket_id, query, confidence_score)
        await update_case_card(
            ticket_id,
            {
                "routing_decision": "collecting",
                "issue_summary": query,
                "student_reply": None,
            },
        )
        return RoutingDecision(
            kind="collecting",
            student_message="",
            ticket_id=ticket_id,
        )

    await _mark_ticket_summary(ticket_id, query, confidence_score)
    candidates = await _load_open_root_tickets(ticket_id)
    match, score, provider = await find_similar_ticket(query, candidates)
    agent_id, channel_name = await _agent_channel_context(session_id)

    if match is not None:
        grouped = await _group_under_parent(ticket_id, match.id, query)
        count = int(grouped["similar_count"])
        parent_id = grouped["parent_id"]
        parent_summary = grouped["parent_summary"]
        parent_escalated_to = grouped["parent_escalated_to"]
        student_message = (
            f"{count} students are facing the same issue — waiting for a reply."
        )
        await update_case_card(
            ticket_id,
            {
                "routing_decision": "grouped",
                "parent_ticket_id": str(parent_id),
                "similar_count": count,
                "routing_score": round(score, 3),
                "llm_provider": provider,
                "student_reply": student_message,
                "issue_summary": query,
            },
        )
        await update_case_card(
            parent_id,
            {
                "similar_count": count,
                "latest_duplicate_ticket_id": str(ticket_id),
            },
        )
        await _speak(agent_id, student_message)
        if channel_name:
            try:
                await notify_coordinator(
                    channel_name=channel_name,
                    poc_contact=parent_escalated_to or "demo-placement-support-desk",
                    summary=(
                        f"Duplicate placement issue grouped under ticket {parent_id}. "
                        f"Now {count} students. Latest: {query[:400]}"
                    ),
                    agent_id=agent_id,
                )
            except AgoraServiceError as exc:
                logger.warning("agora_coordinator_group_notify_failed error=%s", exc)
        return RoutingDecision(
            kind="grouped",
            student_message=student_message,
            ticket_id=ticket_id,
            parent_ticket_id=parent_id,
            similar_count=count,
            matched_summary=parent_summary,
            llm_provider=provider,
            routing_score=score,
        )

    student_message = CONNECTING_MESSAGE
    await update_case_card(
        ticket_id,
        {
            "routing_decision": "escalated",
            "student_reply": student_message,
            "issue_summary": query,
            "similar_count": 1,
            "llm_provider": provider or "none",
            "routing_score": round(score, 3) if score else None,
        },
    )
    await _speak(agent_id, student_message)
    escalation = await trigger_escalation(session_id, ticket_id)
    await update_case_card(
        ticket_id,
        {"escalation": escalation, "student_reply": student_message},
    )
    return RoutingDecision(
        kind="escalated",
        student_message=student_message,
        ticket_id=ticket_id,
        similar_count=1,
        llm_provider=provider,
        routing_score=score,
    )
