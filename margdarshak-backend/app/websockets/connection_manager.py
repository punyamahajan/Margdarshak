import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.db.session_factory import get_session_factory
from app.models.chat_bridge import BridgeStatus, ChatBridge
from app.services.matchmaker_service import MatchmakerError, add_message, get_messages

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[uuid.UUID, dict[uuid.UUID, WebSocket]] = {}

    async def connect(
        self, bridge_id: uuid.UUID, student_id: uuid.UUID, websocket: WebSocket
    ) -> None:
        await websocket.accept()
        self.connections.setdefault(bridge_id, {})[student_id] = websocket

    def disconnect(self, bridge_id: uuid.UUID, student_id: uuid.UUID) -> None:
        bridge_connections = self.connections.get(bridge_id)
        if bridge_connections is None:
            return
        bridge_connections.pop(student_id, None)
        if not bridge_connections:
            self.connections.pop(bridge_id, None)

    async def broadcast(self, bridge_id: uuid.UUID, message: dict[str, Any]) -> None:
        stale_connections: list[uuid.UUID] = []
        for viewer_id, websocket in self.connections.get(bridge_id, {}).items():
            try:
                await websocket.send_json(_public_message(message, viewer_id))
            except Exception:
                stale_connections.append(viewer_id)
        for viewer_id in stale_connections:
            self.disconnect(bridge_id, viewer_id)


manager = ConnectionManager()


def _public_message(message: dict[str, Any], viewer_id: uuid.UUID) -> dict[str, Any]:
    sender_id = message.get("sender_id")
    if sender_id == "system":
        sender = "system"
    elif sender_id == str(viewer_id):
        sender = "self"
    else:
        sender = "peer"
    return {
        "sender": sender,
        "content": message.get("content", ""),
        "sent_at": message.get("sent_at"),
    }


async def _get_participant_bridge(
    bridge_id: uuid.UUID, student_id: uuid.UUID
) -> ChatBridge | None:
    async with get_session_factory()() as db:
        bridge = await db.get(ChatBridge, bridge_id)
    if bridge is None:
        return None
    if bridge.status != BridgeStatus.ACTIVE:
        return None
    if bridge.expires_at <= datetime.now(timezone.utc):
        return None
    if student_id not in (bridge.student_a_id, bridge.student_b_id):
        return None
    return bridge


@router.websocket("/ws/matchmaker/{bridge_id}")
async def matchmaker_chat(
    websocket: WebSocket,
    bridge_id: uuid.UUID,
    # TODO: Derive student_id from authenticated WebSocket claims.
    student_id: uuid.UUID = Query(...),
) -> None:
    bridge = await _get_participant_bridge(bridge_id, student_id)
    if bridge is None:
        await websocket.close(code=1008, reason="inactive bridge or invalid participant")
        return

    await manager.connect(bridge_id, student_id, websocket)
    try:
        history = [
            _public_message(message, student_id)
            for message in await get_messages(bridge_id)
        ]
        await websocket.send_json({"type": "history", "messages": history})

        while True:
            content = await websocket.receive_text()
            if len(content) > 4000:
                await websocket.send_json(
                    {"type": "error", "message": "message exceeds 4000 characters"}
                )
                continue
            try:
                message = await add_message(bridge_id, student_id, content)
            except MatchmakerError as exc:
                await websocket.close(code=1008, reason=str(exc))
                return
            await manager.broadcast(bridge_id, message)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(bridge_id, student_id)
