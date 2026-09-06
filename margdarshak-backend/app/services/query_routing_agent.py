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
from sqlalchemy import or_, select, update

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
    "me", "my", "of", "on", "or", "please", "the", "to", "with", "that", "this",
}

ACK_PATTERN = re.compile(
    r"^\s*(yes|yeah|yep|yup|no|nope|ok|okay|sure|thanks|thank you|"
    r"hi|hello|hey|urgent|it is|it is urgent|yes it is)\s*[.!]?\s*$",
    re.IGNORECASE,
)
PLACEMENT_PATTERN = re.compile(
    r"\b(placement|drive|company|interview|job|application|apply|portal|"
    r"assessment|oa|deadline|offer|resume|cv|document|eligible|eligibility|"
    r"riverbank|acme|northstar|greenfield|fintech|link|url|test|exam|"
    r"tcs|amazon|infosys|wipro|accenture|google|microsoft|deloitte)\b",
    re.IGNORECASE,
)
ISSUE_PATTERN = re.compile(
    r"\b(not working|failed|failing|rejected|reject|error|issue|problem|"
    r"unable|cannot|can't|won't|expired|blocked|missing|stuck|broken|down|"
    r"upload|login|submit|open|reopen|access|404|timeout|crash)\b",
    re.IGNORECASE,
)
COMPANY_PATTERN = re.compile(
    r"\b(riverbank|acme|northstar|greenfield|fintech|tcs|infosys|amazon|google|"
    r"wipro|accenture|microsoft|deloitte|cognizant|capgemini|ibm|oracle|cisco|"
    r"placement portal|college portal|campus portal|portal)\b",
    re.IGNORECASE,
)

SYNONYM_MAP: dict[str, str] = {
    "test": "assessment",
    "exam": "assessment",
    "oa": "assessment",
    "coding": "assessment",
    "url": "link",
    "website": "link",
    "webpage": "link",
    "failing": "broken",
    "failed": "broken",
    "error": "broken",
    "glitch": "broken",
    "issue": "broken",
    "problem": "broken",
    "crash": "broken",
    "down": "broken",
    "fintech": "riverbank",
    "cloud": "acme",
    "analytics": "northstar",
    "cv": "resume",
    "uploading": "upload",
    "submitting": "submit",
    "submission": "submit",
    "ineligible": "eligibility",
    "cgpa": "eligibility",
    "criteria": "eligibility",
}


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


def _extract_company_name(text: str) -> str | None:
    text_lower = text.lower()
    mapping = {
        "riverbank": "Riverbank Fintech Labs",
        "fintech": "Riverbank Fintech Labs",
        "acme": "Acme Cloud Systems",
        "northstar": "Northstar Analytics",
        "greenfield": "Greenfield Robotics",
        "tcs": "TCS",
        "infosys": "Infosys",
        "amazon": "Amazon",
        "google": "Google",
        "wipro": "Wipro",
        "accenture": "Accenture",
        "microsoft": "Microsoft",
        "deloitte": "Deloitte",
        "cognizant": "Cognizant",
        "capgemini": "Capgemini",
        "portal": "Placement Portal",
    }
    for key, name in mapping.items():
        if key in text_lower:
            return name
    return None


def is_routable_query(text: str) -> bool:
    """Route once the student has described both the company/target and a concrete issue."""

    query = " ".join(text.split()).strip()
    if len(query) < 15 or ACK_PATTERN.match(query):
        return False
    has_company = bool(COMPANY_PATTERN.search(query))
    has_placement = bool(PLACEMENT_PATTERN.search(query))
    has_issue = bool(ISSUE_PATTERN.search(query))

    if has_company and has_issue:
        return True
    if has_company and has_placement and len(query) >= 28:
        return True
    return False


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def _canonical_tokens(text: str) -> set[str]:
    raw_tokens = _tokenize(text)
    return {SYNONYM_MAP.get(token, token) for token in raw_tokens}


def _lexical_similarity(left: str, right: str) -> float:
    left_tokens = _canonical_tokens(left)
    right_tokens = _canonical_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = left_tokens.intersection(right_tokens)
    if not overlap:
        return 0.0

    overlap_coef = len(overlap) / min(len(left_tokens), len(right_tokens))
    jaccard = len(overlap) / len(left_tokens.union(right_tokens))

    companies = {
        "riverbank", "acme", "northstar", "greenfield", "tcs", "infosys", "amazon",
        "google", "wipro", "accenture", "microsoft", "deloitte", "cognizant",
    }
    issues = {
        "assessment", "link", "broken", "upload", "submit", "login", "eligibility",
        "resume", "backlog", "deadline", "slot", "clash",
    }

    left_companies = left_tokens.intersection(companies)
    right_companies = right_tokens.intersection(companies)

    # Different companies must never match
    if left_companies and right_companies and left_companies != right_companies:
        return 0.0

    # If one query specifies a company and the other doesn't, reject
    if (left_companies and not right_companies) or (right_companies and not left_companies):
        return 0.0

    has_same_company = bool(overlap.intersection(companies))
    has_same_issue = bool(overlap.intersection(issues))

    # If both queries describe the same company and the same issue type
    if has_same_company and has_same_issue:
        return max(overlap_coef, 0.85)
    # If both describe the same company and an assessment/link issue
    if has_same_company and ("assessment" in overlap or "link" in overlap):
        return max(overlap_coef, 0.80)
    # If both describe a portal failure
    if "portal" in overlap and has_same_issue:
        return max(overlap_coef, 0.78)

    return (overlap_coef * 0.7) + (jaccard * 0.3)


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
        "EXISTING OPEN TICKETS.\n"
        "Students frequently describe the exact same problem using different wording. For example:\n"
        "- 'Riverbank OA link not opening' matches 'Riverbank test link broken 404' or 'cannot open assessment url for riverbank'\n"
        "- 'Acme cloud portal crash on submit' matches 'unable to submit assessment for Acme' or 'Acme test submit error'\n"
        "- 'Northstar interview clash' matches 'Northstar analytics slot conflict with lab exam'\n"
        "- 'Placement portal OTP not arriving' matches 'cannot login to placement portal OTP failed'\n\n"
        "Rules:\n"
        "1. If the company or context matches AND the core blocker/issue category is the same, this is a MATCH.\n"
        "2. Score >= 0.70 (e.g., 0.85-0.95) when they describe the same underlying grievance or drive.\n"
        "3. Only set match=false if they clearly refer to different companies or completely unrelated topics (e.g. resume formatting vs online assessment 404).\n\n"
        "Reply with JSON only:\n"
        '{"match": true|false, "ticket_id": "<uuid or null>", "score": 0.0-1.0, "reason": "short"}\n'
        "Set match=true when score >= 0.65.\n\n"
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
        if matched is not None and score >= min(threshold, 0.65):
            return matched, score, provider

    best_ticket: Ticket | None = None
    best_score = 0.0
    for ticket in candidates:
        score = _lexical_similarity(query, ticket.issue_summary)
        if score > best_score:
            best_ticket = ticket
            best_score = score
    # Lexical fallback with canonical domain weighting
    lexical_threshold = min(max(threshold, 0.50), 0.65)
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
            new_count = int(parent.similar_count or 1) + 1
            parent.similar_count = new_count
            ticket.similar_count = new_count
            # Propagate updated similar_count to all sibling child tickets as well
            await db.execute(
                update(Ticket)
                .where(Ticket.parent_ticket_id == parent.id)
                .values(similar_count=new_count)
            )
            await db.flush()
            return {
                "parent_id": parent.id,
                "parent_summary": parent.issue_summary,
                "parent_escalated_to": parent.escalated_to,
                "similar_count": new_count,
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


async def _is_ticket_already_escalated(ticket_id: uuid.UUID) -> bool:
    try:
        async with get_session_factory()() as db:
            ticket = await db.get(Ticket, ticket_id)
            return bool(ticket and ticket.status == TicketStatus.ESCALATED)
    except Exception:
        return False


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
        if re.search(r"\b(test|oa|assessment|exam|link|url)\b", query, re.IGNORECASE):
            clarification_msg = "Which company or placement drive is this test link for?"
        elif re.search(r"\b(interview|slot|clash)\b", query, re.IGNORECASE):
            clarification_msg = "Which company is this interview clash for?"
        elif re.search(r"\b(resume|cv|document|upload)\b", query, re.IGNORECASE):
            clarification_msg = "Which company's portal are you trying to upload documents to?"
        else:
            clarification_msg = "Which company or placement drive are you facing this issue with?"

        await update_case_card(
            ticket_id,
            {
                "routing_decision": "collecting",
                "issue_summary": query,
                "student_reply": clarification_msg,
            },
        )
        return RoutingDecision(
            kind="collecting",
            student_message=clarification_msg,
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
        company = _extract_company_name(query) or _extract_company_name(parent_summary)
        student_message = (
            f"{count} students are facing the same issue — waiting for a reply."
        )
        if company:
            student_message = (
                f"{count} students are facing the same issue — waiting for a reply. "
                f"I have grouped your report for {company} and alerted the placement coordinator."
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

    if await _is_ticket_already_escalated(ticket_id):
        await update_case_card(
            ticket_id,
            {
                "issue_summary": query,
                "routing_score": round(score, 3) if score else None,
            },
        )
        return RoutingDecision(
            kind="escalated",
            student_message="",
            ticket_id=ticket_id,
            similar_count=1,
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
