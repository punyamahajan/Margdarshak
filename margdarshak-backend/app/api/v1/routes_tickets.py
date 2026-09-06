import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.ticket import Ticket, TicketStatus
from app.schemas.ticket import TicketRead
from app.services.case_card_service import CaseCardNotFoundError, get_case_card

router = APIRouter(prefix="/tickets", tags=["tickets"])


class TicketWithCaseCard(TicketRead):
    case_card: dict[str, Any] | None = None


async def _serialize_ticket(ticket: Ticket) -> TicketWithCaseCard:
    try:
        case_card = await get_case_card(ticket.id)
    except CaseCardNotFoundError:
        case_card = None
    return TicketWithCaseCard.model_validate(ticket).model_copy(
        update={"case_card": case_card}
    )


@router.get("/{ticket_id}", response_model=TicketWithCaseCard)
async def get_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> TicketWithCaseCard:
    ticket = await db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    return await _serialize_ticket(ticket)


@router.get("", response_model=list[TicketWithCaseCard])
async def list_tickets(
    status: TicketStatus | None = None,
    student_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[TicketWithCaseCard]:
    statement = select(Ticket).order_by(Ticket.created_at.desc())
    if status is not None:
        statement = statement.where(Ticket.status == status)
    if student_id is not None:
        statement = statement.where(Ticket.student_id == student_id)
    tickets = (await db.scalars(statement)).all()
    return [await _serialize_ticket(ticket) for ticket in tickets]
