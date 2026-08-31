import uuid
from datetime import datetime

from app.schemas.base import ORMModel


class ConsentRevealCreate(ORMModel):
    bridge_id: uuid.UUID
    student_id: uuid.UUID


class ConsentRevealRead(ConsentRevealCreate):
    id: uuid.UUID
    consented_at: datetime
