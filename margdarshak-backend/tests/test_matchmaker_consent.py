import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from app.api.v1.routes_matchmaker import RevealResponse
from app.models.chat_bridge import BridgeStatus, ChatBridge
from app.services import matchmaker_service


class AsyncContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeSession(AsyncContext):
    def __init__(self, bridge: ChatBridge) -> None:
        self.bridge = bridge

    def begin(self) -> AsyncContext:
        return AsyncContext()

    async def scalar(self, statement):
        return self.bridge


def test_single_reveal_consent_never_returns_linkedin_url(monkeypatch) -> None:
    student_a_id = uuid.uuid4()
    bridge = ChatBridge(
        id=uuid.uuid4(),
        student_a_id=student_a_id,
        student_b_id=uuid.uuid4(),
        match_reason="Shared robotics",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        status=BridgeStatus.ACTIVE,
    )
    fake_session = FakeSession(bridge)

    async def only_one_student_consented(db, locked_bridge, student_id, purpose):
        assert student_id == student_a_id
        return False

    monkeypatch.setattr(
        matchmaker_service, "get_session_factory", lambda: lambda: fake_session
    )
    monkeypatch.setattr(
        matchmaker_service, "_record_dual_consent", only_one_student_consented
    )

    result = asyncio.run(
        matchmaker_service.request_reveal(bridge.id, student_a_id)
    )
    serialized = RevealResponse(**result).model_dump(exclude_none=True)

    assert serialized == {"status": "pending"}
    assert "linkedin_urls" not in serialized
