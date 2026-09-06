import asyncio
import uuid

from app.models.ticket import Ticket, TicketStatus
from app.services import query_routing_agent


def test_lexical_similarity_groups_obvious_duplicates() -> None:
    left = "TCS portal is not accepting my resume upload before the deadline"
    right = "The TCS portal will not accept resume upload before deadline"
    score = query_routing_agent._lexical_similarity(left, right)
    assert score >= 0.5


def test_is_routable_query_requires_concrete_issue() -> None:
    assert not query_routing_agent.is_routable_query("help me")
    assert not query_routing_agent.is_routable_query("yes")
    assert query_routing_agent.is_routable_query(
        "The TCS placement portal is rejecting my resume upload before the deadline"
    )


def test_find_similar_ticket_uses_lexical_fallback(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    from app.core.config import get_settings

    get_settings.cache_clear()

    existing = Ticket(
        id=uuid.uuid4(),
        student_id=uuid.uuid4(),
        issue_summary="Amazon OA link expired and I cannot reopen the assessment",
        transcript_ref=str(uuid.uuid4()),
        confidence_score=0.4,
        status=TicketStatus.OPEN,
        escalated_to="",
        roll_number_snapshot="R1",
        similar_count=1,
    )
    query = "Amazon OA assessment link expired and I cannot reopen it"

    async def no_llm(*_args, **_kwargs):
        return None, None

    monkeypatch.setattr(query_routing_agent, "_call_llm_similarity", no_llm)

    try:
        match, score, provider = asyncio.run(
            query_routing_agent.find_similar_ticket(query, [existing])
        )
    finally:
        get_settings.cache_clear()

    assert match is not None
    assert match.id == existing.id
    assert score >= 0.5
    assert provider == "lexical"


def test_route_student_query_collects_incomplete_text(monkeypatch) -> None:
    async def fake_mark(*_args, **_kwargs):
        return None

    async def fake_update(_ticket_id, fields):
        return fields

    monkeypatch.setattr(query_routing_agent, "_mark_ticket_summary", fake_mark)
    monkeypatch.setattr(query_routing_agent, "update_case_card", fake_update)

    decision = asyncio.run(
        query_routing_agent.route_student_query(
            uuid.uuid4(), uuid.uuid4(), "help me"
        )
    )
    assert decision.kind == "collecting"


def test_speak_path_is_used_when_grouping(monkeypatch) -> None:
    session_id = uuid.uuid4()
    ticket_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    spoken: list[str] = []
    notified: list[str] = []

    parent = Ticket(
        id=parent_id,
        student_id=uuid.uuid4(),
        issue_summary="Infosys portal rejected my documents repeatedly",
        transcript_ref=str(uuid.uuid4()),
        confidence_score=0.3,
        status=TicketStatus.OPEN,
        escalated_to="desk",
        roll_number_snapshot="R2",
        similar_count=2,
    )

    async def fake_mark(*_args, **_kwargs):
        return None

    async def fake_load(_exclude):
        return [parent]

    async def fake_find(query, candidates):
        return parent, 0.9, "gemini"

    async def fake_group(ticket_id_arg, parent_ticket_id, issue_summary):
        return {
            "parent_id": parent_id,
            "parent_summary": parent.issue_summary,
            "parent_escalated_to": "desk",
            "similar_count": 3,
        }

    async def fake_context(_session_id):
        return "agent-1", "channel-1"

    async def fake_update(_ticket_id, fields):
        return fields

    async def fake_speak(agent_id, text, **_kwargs):
        spoken.append(text)
        return {"status": "spoken"}

    async def fake_notify(**kwargs):
        notified.append(kwargs["summary"])
        return {"status": "handover_pending"}

    monkeypatch.setattr(query_routing_agent, "_mark_ticket_summary", fake_mark)
    monkeypatch.setattr(query_routing_agent, "_load_open_root_tickets", fake_load)
    monkeypatch.setattr(query_routing_agent, "find_similar_ticket", fake_find)
    monkeypatch.setattr(query_routing_agent, "_group_under_parent", fake_group)
    monkeypatch.setattr(query_routing_agent, "_agent_channel_context", fake_context)
    monkeypatch.setattr(query_routing_agent, "update_case_card", fake_update)
    monkeypatch.setattr(query_routing_agent, "speak_to_student", fake_speak)
    monkeypatch.setattr(query_routing_agent, "notify_coordinator", fake_notify)

    decision = asyncio.run(
        query_routing_agent.route_student_query(
            session_id,
            ticket_id,
            "Infosys portal keeps rejecting my documents repeatedly",
        )
    )

    assert decision.kind == "grouped"
    assert decision.similar_count == 3
    assert "3 students are facing the same issue" in decision.student_message
    assert spoken and "3 students" in spoken[0]
    assert notified


def test_escalated_message_is_short(monkeypatch) -> None:
    session_id = uuid.uuid4()
    ticket_id = uuid.uuid4()
    spoken: list[str] = []

    async def fake_mark(*_args, **_kwargs):
        return None

    async def fake_load(_exclude):
        return []

    async def fake_find(query, candidates):
        return None, 0.0, "gemini"

    async def fake_context(_session_id):
        return "agent-1", "channel-1"

    async def fake_update(_ticket_id, fields):
        return fields

    async def fake_speak(agent_id, text, **_kwargs):
        spoken.append(text)
        return {"status": "spoken"}

    async def fake_escalate(*_args, **_kwargs):
        return {"triggered": True}

    monkeypatch.setattr(query_routing_agent, "_mark_ticket_summary", fake_mark)
    monkeypatch.setattr(query_routing_agent, "_load_open_root_tickets", fake_load)
    monkeypatch.setattr(query_routing_agent, "find_similar_ticket", fake_find)
    monkeypatch.setattr(query_routing_agent, "_agent_channel_context", fake_context)
    monkeypatch.setattr(query_routing_agent, "update_case_card", fake_update)
    monkeypatch.setattr(query_routing_agent, "speak_to_student", fake_speak)
    monkeypatch.setattr(query_routing_agent, "trigger_escalation", fake_escalate)

    decision = asyncio.run(
        query_routing_agent.route_student_query(
            session_id,
            ticket_id,
            "Amazon placement portal is not accepting my application documents",
        )
    )
    assert decision.kind == "escalated"
    assert decision.student_message == "Connecting to coordinator."
    assert spoken == ["Connecting to coordinator."]
