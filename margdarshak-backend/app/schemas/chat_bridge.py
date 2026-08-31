import uuid
from datetime import datetime

from app.models.chat_bridge import BridgeStatus
from app.schemas.base import ORMModel


class ChatBridgeCreate(ORMModel):
    student_a_id: uuid.UUID
    student_b_id: uuid.UUID
    match_reason: str
    expires_at: datetime
    status: BridgeStatus


class ChatBridgeRead(ChatBridgeCreate):
    id: uuid.UUID
    created_at: datetime
