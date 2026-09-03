import asyncio
import json
import uuid

from app.services import resource_diagnostic_orchestrator as orchestrator
from app.services import resource_diagnostic_service
from app.models.resource import (
    Resource,
    ResourceFormat,
    ResourcePacing,
    ResourcePriceTier,
)
from app.services.resource_diagnostic_service import extract_criteria


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def set(self, key: str, value: str, **_kwargs):
        self.values[key] = value


def test_extract_criteria_returns_stable_shape_and_ignores_agent_prompts() -> None:
    result = extract_criteria(
        [
            {
                "speaker": "agent",
                "content": "Short or long? Sheet or video? Free or paid?",
            },
            {"speaker": "student", "content": "Java DSA, deep dive, paid videos."},
        ]
    )

    assert result == {
        "skill": "dsa",
        "pacing": "long",
        "format": "video",
        "budget": "paid",
    }


def test_extract_criteria_handles_common_voice_transcription_variants() -> None:
    result = extract_criteria(
        [
            {"speaker": "student", "content": "development"},
            {"speaker": "student", "content": "shortcut"},
        ]
    )

    assert result["skill"] == "web_dev"
    assert result["pacing"] == "short"


def test_explicit_link_request_uses_defaults_and_recommends(monkeypatch) -> None:
    session_id = uuid.uuid4()
    student_id = uuid.uuid4()
    ticket_id = uuid.uuid4()
    redis = FakeRedis()
    captured_criteria = None

    async def fake_append_turn(*_args):
        return None

    async def fake_recommend(_student_id, _session_id, criteria):
        nonlocal captured_criteria
        captured_criteria = dict(criteria)
        return Resource(
            id=uuid.uuid4(),
            skill_tag="web_dev",
            format=ResourceFormat.SHEET,
            pacing=ResourcePacing.SHORT,
            price_tier=ResourcePriceTier.FREE,
            url="https://example.invalid/web",
            title="Web resource",
        )

    async def fake_update_case_card(*_args):
        return None

    async def fake_student_id_for_session(_session_id):
        return student_id

    async def fake_ticket_id_for_session(_session_id):
        return ticket_id

    monkeypatch.setattr(orchestrator, "get_redis_client", lambda: redis)
    monkeypatch.setattr(orchestrator, "append_turn", fake_append_turn)
    monkeypatch.setattr(orchestrator, "recommend", fake_recommend)
    monkeypatch.setattr(
        orchestrator, "_student_id_for_session", fake_student_id_for_session
    )
    monkeypatch.setattr(
        orchestrator, "_ticket_id_for_session", fake_ticket_id_for_session
    )
    monkeypatch.setattr(orchestrator, "update_case_card", fake_update_case_card)

    result = asyncio.run(
        orchestrator.handle_resource_turn(
            session_id, "development, please place the link in the box"
        )
    )
    assert result["complete"] is True
    assert captured_criteria == {
        "skill": "web_dev",
        "pacing": "short",
        "format": "sheet",
        "budget": "free",
    }


def test_resource_flow_asks_in_order_then_recommends(monkeypatch) -> None:
    session_id = uuid.uuid4()
    redis = FakeRedis()
    persisted_turns: list[tuple[str, str]] = []

    async def fake_append_turn(_session_id, speaker, content):
        persisted_turns.append((speaker.value, content))

    student_id = uuid.uuid4()

    async def fake_recommend(requested_student_id, requested_session_id, criteria):
        assert requested_student_id == student_id
        assert requested_session_id == session_id
        assert criteria == {
            "skill": "system_design",
            "pacing": "short",
            "format": "sheet",
            "budget": "free",
        }
        return Resource(
            id=uuid.uuid4(),
            skill_tag="system_design",
            format=ResourceFormat.SHEET,
            pacing=ResourcePacing.SHORT,
            price_tier=ResourcePriceTier.FREE,
            url="https://example.invalid/resource",
            title="Test resource",
        )

    async def fake_student_id_for_session(requested_session_id):
        assert requested_session_id == session_id
        return student_id

    ticket_id = uuid.uuid4()

    async def fake_ticket_id_for_session(requested_session_id):
        assert requested_session_id == session_id
        return ticket_id

    async def fake_update_case_card(requested_ticket_id, fields):
        assert requested_ticket_id == ticket_id
        assert fields

    monkeypatch.setattr(orchestrator, "get_redis_client", lambda: redis)
    monkeypatch.setattr(orchestrator, "append_turn", fake_append_turn)
    monkeypatch.setattr(orchestrator, "recommend", fake_recommend)
    monkeypatch.setattr(
        orchestrator, "_student_id_for_session", fake_student_id_for_session
    )
    monkeypatch.setattr(
        orchestrator, "_ticket_id_for_session", fake_ticket_id_for_session
    )
    monkeypatch.setattr(orchestrator, "update_case_card", fake_update_case_card)

    first = asyncio.run(
        orchestrator.handle_resource_turn(session_id, "I want System Design")
    )
    second = asyncio.run(orchestrator.handle_resource_turn(session_id, "A short crash course"))
    third = asyncio.run(orchestrator.handle_resource_turn(session_id, "A free hands-on sheet"))

    assert first["question"].startswith("Do you want a short")
    assert second["question"].startswith("Would you prefer")
    assert third["complete"] is True
    assert [speaker for speaker, _ in persisted_turns] == [
        "student",
        "agent",
        "student",
        "agent",
        "student",
    ]
    state = json.loads(redis.values[f"resource-diagnostic:session:{session_id}"])
    assert state["complete"] is True


class FakeScalarResult:
    def __init__(self, resource):
        self.resource = resource

    def first(self):
        return self.resource


class FakeResourceSession:
    def __init__(self, final_resource: Resource) -> None:
        self.final_resource = final_resource
        self.where_clauses: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def scalars(self, statement):
        rendered = str(statement)
        where_clause = rendered.split("WHERE", 1)[1].split("ORDER BY", 1)[0]
        self.where_clauses.append(where_clause)
        resource = self.final_resource if len(self.where_clauses) == 4 else None
        return FakeScalarResult(resource)


def test_find_best_resource_relaxes_price_then_format_then_pacing(monkeypatch) -> None:
    selected = Resource(
        id=uuid.uuid4(),
        skill_tag="dsa",
        format=ResourceFormat.VIDEO,
        pacing=ResourcePacing.LONG,
        price_tier=ResourcePriceTier.PAID,
        url="https://example.invalid/dsa",
        title="Fallback DSA resource",
    )
    fake_session = FakeResourceSession(selected)
    monkeypatch.setattr(
        resource_diagnostic_service,
        "get_session_factory",
        lambda: lambda: fake_session,
    )

    result = asyncio.run(
        resource_diagnostic_service.find_best_resource(
            {
                "skill": "dsa",
                "pacing": "short",
                "format": "sheet",
                "budget": "free",
            }
        )
    )

    assert result is selected
    exact, price_relaxed, format_relaxed, pacing_relaxed = fake_session.where_clauses
    assert "resources.price_tier" in exact
    assert "resources.format" in exact and "resources.pacing" in exact
    assert "resources.price_tier" not in price_relaxed
    assert "resources.format" in price_relaxed and "resources.pacing" in price_relaxed
    assert "resources.format" not in format_relaxed
    assert "resources.pacing" in format_relaxed
    assert "resources.pacing" not in pacing_relaxed
