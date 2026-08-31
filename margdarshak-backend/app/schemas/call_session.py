import uuid
from datetime import datetime

from app.models.call_session import CallFlowType
from app.schemas.base import ORMModel


class CallSessionCreate(ORMModel):
    agora_channel_id: str
    student_id: uuid.UUID
    started_at: datetime | None = None
    ended_at: datetime | None = None
    flow_type: CallFlowType


class CallSessionRead(CallSessionCreate):
    id: uuid.UUID
    started_at: datetime
