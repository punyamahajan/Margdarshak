import asyncio

import httpx
import pytest

from app.core.config import get_settings
from app.services import agora_service


class _FakeResponse:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"agent_id": "runtime-agent-123", "state": "active"}


class _FakeClient:
    last_request: dict[str, object] = {}

    def __init__(self, **_: object) -> None:
        pass

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, url: str, **kwargs: object) -> _FakeResponse:
        self.last_request = {"url": url, **kwargs}
        _FakeClient.last_request = self.last_request
        return _FakeResponse()


def test_start_agent_uses_published_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGORA_CUSTOMER_ID", "customer-id")
    monkeypatch.setenv("AGORA_CUSTOMER_SECRET", "customer-secret")
    monkeypatch.setenv("AGORA_AI_AGENT", "published-pipeline-id")
    monkeypatch.setenv("AGORA_AGENT_RTC_UID", "1")
    get_settings.cache_clear()
    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)
    monkeypatch.setattr(agora_service, "generate_rtc_token", lambda *_: "agent-token")

    try:
        result = asyncio.run(agora_service.start_agent_session("test-channel", 42))
    finally:
        get_settings.cache_clear()

    assert result["agent_id"] == "runtime-agent-123"
    assert result["status"] == "active"
    request = _FakeClient.last_request
    assert request["url"].endswith("/test-app-id/join")
    assert request["auth"] == ("customer-id", "customer-secret")
    body = request["json"]
    assert isinstance(body, dict)
    assert body["pipeline_id"] == "published-pipeline-id"
    properties = body["properties"]
    assert isinstance(properties, dict)
    assert {key: properties[key] for key in (
        "channel", "token", "agent_rtc_uid", "remote_rtc_uids",
        "enable_string_uid", "idle_timeout",
    )} == {
        "channel": "test-channel",
        "token": "agent-token",
        "agent_rtc_uid": "1",
        "remote_rtc_uids": ["42"],
        "enable_string_uid": False,
        "idle_timeout": 120,
    }
    assert properties["advanced_features"] == {"enable_rtm": True}
    assert properties["parameters"]["data_channel"] == "rtm"
    assert "Never ask for facts already present" in properties["llm"]["system_messages"][0]["content"]
    assert "Do NOT ask whether the issue is urgent" in properties["llm"]["system_messages"][0]["content"]
    assert "support chatbot" in properties["llm"]["system_messages"][0]["content"].lower()
    assert "Tell me what you need" in properties["llm"]["greeting_message"]
