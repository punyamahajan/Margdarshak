import re
import uuid
from collections.abc import Iterable

from sqlalchemy import select

from app.db.session_factory import get_session_factory
from app.models.admin import TicketCluster, TicketWorkflow
from app.models.placement_drive import PlacementDrive
from app.models.ticket import Ticket

URGENCY_WEIGHT = {"low": 1, "medium": 2, "high": 3, "critical": 4}
STOP_WORDS = {"a", "an", "and", "for", "i", "is", "it", "my", "not", "of", "the", "to"}


def classify_issue(text: str) -> str:
    value = text.lower()
    rules = (
        ("Technical / Assessment", ("assessment", "test", "link", "timeout")),
        ("Eligibility", ("eligible", "eligibility", "cgpa", "backlog")),
        ("Interview", ("interview", "schedule", "round")),
        ("Application", ("apply", "application", "portal")),
        ("Document", ("document", "resume", "certificate")),
        ("Shortlisting", ("shortlist", "selected")),
        ("Deadline", ("deadline", "last date")),
    )
    return next((category for category, words in rules if any(word in value for word in words)), "Other")


def issue_similarity(left: str, right: str) -> float:
    def tokens(value: str) -> set[str]:
        return {word for word in re.findall(r"[a-z0-9]+", value.lower()) if word not in STOP_WORDS}
    a, b = tokens(left), tokens(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def calculate_priority(affected: int, urgencies: Iterable[str], *, blocked: bool = False, deadline_days: int | None = None) -> tuple[int, str]:
    highest = max((URGENCY_WEIGHT.get(value, 2) for value in urgencies), default=2)
    score = min(100, affected * 5 + highest * 12 + (15 if blocked else 0) + (20 if deadline_days is not None and deadline_days <= 1 else 10 if deadline_days is not None and deadline_days <= 3 else 0))
    return score, "critical" if score >= 70 else "high" if score >= 50 else "medium" if score >= 30 else "low"


async def sync_ticket_workflow(ticket_id: uuid.UUID, issue_summary: str, confidence: float, urgent: bool, resolved_from_knowledge: bool = False) -> None:
    """Persist AI triage fields and automatically group a repeated placement issue."""
    category = classify_issue(issue_summary)
    urgency = "high" if urgent else "medium"
    async with get_session_factory()() as db:
        async with db.begin():
            ticket = await db.get(Ticket, ticket_id, with_for_update=True)
            if ticket is None:
                return
            ticket.issue_summary = issue_summary
            ticket.confidence_score = confidence
            workflow = await db.get(TicketWorkflow, ticket_id)
            if workflow is None:
                workflow = TicketWorkflow(ticket_id=ticket_id)
                db.add(workflow)
            workflow.category = category
            workflow.urgency = urgency
            if resolved_from_knowledge:
                workflow.status = "resolved"
            workflow.original_request = issue_summary
            workflow.conversation_summary = issue_summary
            candidates = [] if resolved_from_knowledge else (await db.execute(select(Ticket, TicketWorkflow).join(TicketWorkflow, TicketWorkflow.ticket_id == Ticket.id).where(Ticket.id != ticket_id, Ticket.drive_id == ticket.drive_id, TicketWorkflow.status != "resolved", TicketWorkflow.category == category))).all()
            match = next(((other, other_flow) for other, other_flow in candidates if issue_similarity(issue_summary, other.issue_summary) >= 0.35), None)
            if match:
                other, other_flow = match
                cluster = await db.get(TicketCluster, other_flow.cluster_id) if other_flow.cluster_id else None
                if cluster is None:
                    company = await db.get(PlacementDrive, ticket.drive_id) if ticket.drive_id else None
                    cluster = TicketCluster(title=issue_summary[:120], company_name=company.company_name if company else None, drive_id=ticket.drive_id, urgency=urgency, status="open")
                    db.add(cluster)
                    await db.flush()
                    other_flow.cluster_id = cluster.id
                workflow.cluster_id = cluster.id
                _, level = calculate_priority(2, [workflow.urgency, other_flow.urgency], blocked="link" in issue_summary.lower())
                cluster.urgency = level
