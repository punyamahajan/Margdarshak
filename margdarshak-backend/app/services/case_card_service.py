import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.db.session_factory import get_session_factory
from app.models.case_card import CaseCard
from app.models.ticket import Ticket

# This repository is the sole application write boundary for `case_cards`.
# Other modules must call update_case_card rather than adding/updating CaseCard.


class CaseCardNotFoundError(LookupError):
    pass


class TicketNotFoundError(LookupError):
    pass


async def update_case_card(
    ticket_id: uuid.UUID, new_fields: dict[str, Any]
) -> dict[str, Any]:
    """Merge fields safely, serializing writers with a parent-ticket row lock."""

    async with get_session_factory()() as session:
        async with session.begin():
            # Locking the always-present parent also serializes first-time card creation.
            locked_ticket_id = await session.scalar(
                select(Ticket.id).where(Ticket.id == ticket_id).with_for_update()
            )
            if locked_ticket_id is None:
                raise TicketNotFoundError(f"ticket {ticket_id} does not exist")

            case_card = await session.scalar(
                select(CaseCard).where(CaseCard.ticket_id == ticket_id)
            )
            if case_card is None:
                case_card = CaseCard(ticket_id=ticket_id, structured_json={})
                session.add(case_card)

            merged_fields = dict(case_card.structured_json or {})
            merged_fields.update(new_fields)
            case_card.structured_json = merged_fields
            case_card.last_updated = datetime.now(timezone.utc)
            await session.flush()

        return dict(case_card.structured_json)


async def get_case_card(ticket_id: uuid.UUID) -> dict[str, Any]:
    async with get_session_factory()() as session:
        structured_json = await session.scalar(
            select(CaseCard.structured_json).where(CaseCard.ticket_id == ticket_id)
        )

    if structured_json is None:
        raise CaseCardNotFoundError(f"case card for ticket {ticket_id} does not exist")
    return dict(structured_json)
