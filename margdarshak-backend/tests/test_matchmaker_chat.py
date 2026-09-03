import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from app.models.chat_bridge import BridgeStatus, ChatBridge
from app.services import matchmaker_service


class FakeRedis:
    def __init__(self, ttl: int) -> None:
        self.current_ttl = ttl
        self.expire_calls: list[int] = []
        self.messages: list[str] = []

    async def rpush(self, key, value):
        self.messages.append(value)

    async def ttl(self, key):
        return self.current_ttl

    async def expire(self, key, seconds):
        self.expire_calls.append(seconds)


def test_generate_icebreaker_mentions_specific_common_context() -> None:
    message = matchmaker_service.generate_icebreaker(
        {"tags": ["FastAPI", "Robotics"]},
        {"tags": ["Robotics", "Design"]},
    )

    assert "Robotics" in message
    assert message.endswith("?")


def test_demo_reply_is_specific_and_transparent() -> None:
    greeting = matchmaker_service.generate_demo_reply("hi")
    backend = matchmaker_service.generate_demo_reply("I am learning FastAPI")

    assert "demo match" in greeting.lower()
    assert "backend" in backend.lower()


def test_add_message_does_not_extend_existing_ttl(monkeypatch) -> None:
    bridge_id = uuid.uuid4()
    bridge = ChatBridge(
        id=bridge_id,
        student_a_id=uuid.uuid4(),
        student_b_id=uuid.uuid4(),
        match_reason="Shared Robotics",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        status=BridgeStatus.ACTIVE,
    )
    redis = FakeRedis(ttl=120)

    async def fake_get_active_bridge(requested_bridge_id):
        assert requested_bridge_id == bridge_id
        return bridge

    monkeypatch.setattr(
        matchmaker_service, "_get_active_bridge", fake_get_active_bridge
    )
    monkeypatch.setattr(matchmaker_service, "get_redis_client", lambda: redis)

    asyncio.run(matchmaker_service.add_message(bridge_id, uuid.uuid4(), "Hello"))

    assert len(redis.messages) == 1
    assert redis.expire_calls == []
