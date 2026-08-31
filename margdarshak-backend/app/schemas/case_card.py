import uuid
from datetime import datetime
from typing import Any

from app.schemas.base import ORMModel


class CaseCardCreate(ORMModel):
    ticket_id: uuid.UUID
    structured_json: dict[str, Any]


class CaseCardRead(CaseCardCreate):
    id: uuid.UUID
    last_updated: datetime
