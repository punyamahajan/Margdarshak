import uuid
from datetime import datetime

from app.models.ticket import TicketStatus
from app.schemas.base import ORMModel


class TicketCreate(ORMModel):
    student_id: uuid.UUID
    drive_id: uuid.UUID | None = None
    issue_summary: str
    transcript_ref: str
    confidence_score: float
    status: TicketStatus
    escalated_to: str
    roll_number_snapshot: str
    parent_ticket_id: uuid.UUID | None = None
    similar_count: int = 1


class TicketRead(TicketCreate):
    id: uuid.UUID
    created_at: datetime
    display_status: str
    display_status_detail: str
