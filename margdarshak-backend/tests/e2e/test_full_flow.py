"""Service-level smoke tests for the complete Margdarshak pipelines.

These tests intentionally use real PostgreSQL and Redis instances. Set both
``E2E_DATABASE_URL`` and ``E2E_REDIS_URL`` after applying all migrations. The
ordinary unit suite skips this module when either value is absent.
"""

import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import delete, insert, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.call_session import CallFlowType, CallSession
from app.models.case_card import CaseCard
from app.models.chat_bridge import BridgeStatus, ChatBridge
from app.models.consent_reveal import ConsentReveal
from app.models.placement_drive import PlacementDrive
from app.models.resource import (
    Resource,
    ResourceFormat,
    ResourcePacing,
    ResourcePriceTier,
    ResourceRecommendation,
)
from app.models.student import Student
from app.models.ticket import Ticket, TicketStatus
from app.models.transcript import Transcript
from app.services import (
    case_card_service,
    conversation_orchestrator,
    escalation_service,
    matchmaker_service,
    resource_diagnostic_orchestrator,
    resource_diagnostic_service,
    transcript_service,
)
from app.workers import expiry_worker


def _required_environment() -> tuple[str, str]:
    database_url = os.getenv("E2E_DATABASE_URL")
    redis_url = os.getenv("E2E_REDIS_URL")
    if not database_url or not redis_url:
        pytest.skip("set E2E_DATABASE_URL and E2E_REDIS_URL to run smoke tests")
    return database_url, redis_url


@asynccontextmanager
async def _real_services(monkeypatch: pytest.MonkeyPatch):
    database_url, redis_url = _required_environment()
    try:
        from redis.asyncio import Redis
    except ImportError as exc:  # pragma: no cover - only possible in incomplete envs
        pytest.fail(f"redis dependency is not installed: {exc}")

    engine = create_async_engine(database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    redis = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            tables = set(
                await connection.run_sync(
                    lambda sync_connection: __import__("sqlalchemy").inspect(
                        sync_connection
                    ).get_table_names()
                )
            )
        required_tables = {
            "students",
            "placement_drives",
            "call_sessions",
            "tickets",
            "case_cards",
            "transcripts",
            "resources",
            "resource_recommendations",
            "chat_bridges",
            "consent_reveals",
        }
        missing = required_tables - tables
        if missing:
            pytest.fail(f"E2E database is not migrated; missing tables: {sorted(missing)}")
        await redis.ping()

        for module in (
            case_card_service,
            conversation_orchestrator,
            escalation_service,
            matchmaker_service,
            resource_diagnostic_orchestrator,
            resource_diagnostic_service,
            transcript_service,
            expiry_worker,
        ):
            if hasattr(module, "get_session_factory"):
                monkeypatch.setattr(module, "get_session_factory", lambda: factory)
            if hasattr(module, "get_redis_client"):
                monkeypatch.setattr(module, "get_redis_client", lambda: redis)

        # conversation_orchestrator imported this function directly.
        from app.db import readonly_gateway

        monkeypatch.setattr(readonly_gateway, "get_session_factory", lambda: factory)
        monkeypatch.setattr(
            conversation_orchestrator,
            "query_drive_policy",
            readonly_gateway.query_drive_policy,
        )
        monkeypatch.setattr(
            escalation_service,
            "query_drive_policy",
            readonly_gateway.query_drive_policy,
        )
        yield engine, factory, redis
    except (OSError, ConnectionError) as exc:
        pytest.fail(f"E2E services are unreachable: {exc}")
    finally:
        await redis.aclose()
        await engine.dispose()


async def _insert_drive(engine: Any, drive_id: uuid.UUID, name: str, poc: str) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            insert(PlacementDrive.__table__).values(
                id=drive_id,
                company_name=name,
                poc_name=f"{name} Test POC",
                poc_contact=poc,
                policy_doc_ref="Round 1: assessment; Round 2: technical interview",
                status="active",
            )
        )


def _student(student_id: uuid.UUID, roll: str, *, tags: list[str] | None = None) -> Student:
    return Student(
        id=student_id,
        roll_number=roll,
        name=f"E2E Student {roll}",
        email=f"{roll}@e2e.example.invalid",
        branch="CSE",
        phone=f"+91-e2e-{roll}",
        linkedin_url=f"https://linkedin.example.invalid/{roll}",
        tags=tags or [],
        matchmaking_opt_in=bool(tags),
    )


async def _create_triage_records(factory: Any, drive_id: uuid.UUID):
    student_id, session_id, ticket_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with factory() as db:
        db.add(_student(student_id, f"e2e-{student_id.hex[:8]}"))
        db.add(
            CallSession(
                id=session_id,
                agora_channel_id=f"e2e-{session_id}",
                student_id=student_id,
                flow_type=CallFlowType.TRIAGE,
            )
        )
        db.add(
            Ticket(
                id=ticket_id,
                student_id=student_id,
                drive_id=drive_id,
                issue_summary="",
                transcript_ref=str(session_id),
                confidence_score=0,
                status=TicketStatus.OPEN,
                escalated_to="",
                roll_number_snapshot="",
            )
        )
        await db.commit()
    await conversation_orchestrator.initialize_triage_session(session_id, ticket_id)
    return student_id, session_id, ticket_id


async def _cleanup_triage(engine: Any, student_id: uuid.UUID, session_id: uuid.UUID, ticket_id: uuid.UUID, drive_id: uuid.UUID) -> None:
    async with engine.begin() as connection:
        await connection.execute(delete(Transcript).where(Transcript.call_session_id == session_id))
        await connection.execute(delete(CaseCard).where(CaseCard.ticket_id == ticket_id))
        await connection.execute(delete(Ticket).where(Ticket.id == ticket_id))
        await connection.execute(delete(CallSession).where(CallSession.id == session_id))
        await connection.execute(delete(Student).where(Student.id == student_id))
        await connection.execute(delete(PlacementDrive.__table__).where(PlacementDrive.id == drive_id))


def test_triage_happy_path_builds_case_card_without_escalation(monkeypatch) -> None:
    async def scenario() -> None:
        async with _real_services(monkeypatch) as (engine, factory, redis):
            drive_id = uuid.uuid4()
            student_id = session_id = ticket_id = None
            escalation_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
            try:
                await _insert_drive(engine, drive_id, f"E2E Policy {drive_id.hex[:6]}", "poc-policy@example.invalid")
                student_id, session_id, ticket_id = await _create_triage_records(factory, drive_id)

                async def unexpected_escalation(call_session_id, requested_ticket_id):
                    escalation_calls.append((call_session_id, requested_ticket_id))
                    return {"triggered": True}

                monkeypatch.setattr(conversation_orchestrator, "trigger_escalation", unexpected_escalation)
                first = await conversation_orchestrator.handle_triage_turn(
                    session_id, f"What is the eligibility policy for drive {drive_id}?"
                )
                second = await conversation_orchestrator.handle_triage_turn(
                    session_id, "Can you confirm the salary package policy?"
                )

                async with factory() as db:
                    card = await db.scalar(select(CaseCard).where(CaseCard.ticket_id == ticket_id))
                    ticket = await db.get(Ticket, ticket_id)
                assert card is not None
                assert card.structured_json["classification"] == "policy_question"
                assert first["confidence_score"] >= 0.9
                assert second["confidence_score"] >= 0.9
                assert escalation_calls == []
                assert ticket is not None and ticket.status == TicketStatus.OPEN
            finally:
                if student_id and session_id and ticket_id:
                    await redis.delete(f"triage:session:{session_id}")
                    await _cleanup_triage(engine, student_id, session_id, ticket_id, drive_id)

    asyncio.run(scenario())


def test_triage_urgent_path_escalates_and_persists_transcript(monkeypatch) -> None:
    async def scenario() -> None:
        async with _real_services(monkeypatch) as (engine, factory, redis):
            drive_id = uuid.uuid4()
            student_id = session_id = ticket_id = None
            trigger_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
            try:
                poc_contact = "urgent-poc@example.invalid"
                await _insert_drive(engine, drive_id, f"E2E Urgent {drive_id.hex[:6]}", poc_contact)
                student_id, session_id, ticket_id = await _create_triage_records(factory, drive_id)

                async def fake_handover(channel_name: str, contact: str, summary: str):
                    assert contact == poc_contact
                    assert "portal is down" in summary.lower()
                    return {"status": "handover_pending", "channel_name": channel_name}

                monkeypatch.setattr(escalation_service, "handover_to_human", fake_handover)
                real_trigger = escalation_service.trigger_escalation

                async def tracked_trigger(call_session_id, requested_ticket_id):
                    trigger_calls.append((call_session_id, requested_ticket_id))
                    return await real_trigger(call_session_id, requested_ticket_id)

                monkeypatch.setattr(conversation_orchestrator, "trigger_escalation", tracked_trigger)
                await conversation_orchestrator.handle_triage_turn(
                    session_id, "The placement portal is down and the deadline is today."
                )

                async with factory() as db:
                    ticket = await db.get(Ticket, ticket_id)
                    transcript_rows = (
                        await db.scalars(
                            select(Transcript)
                            .where(Transcript.call_session_id == session_id)
                            .order_by(Transcript.turn_index)
                        )
                    ).all()
                assert trigger_calls == [(session_id, ticket_id)]
                assert ticket is not None and ticket.status == TicketStatus.ESCALATED
                assert ticket.escalated_to == poc_contact
                assert transcript_rows
                assert "portal is down" in transcript_rows[0].content.lower()
            finally:
                if student_id and session_id and ticket_id:
                    await redis.delete(f"triage:session:{session_id}")
                    await _cleanup_triage(engine, student_id, session_id, ticket_id, drive_id)

    asyncio.run(scenario())


def test_resource_diagnostic_persists_recommendation_and_notifies(monkeypatch) -> None:
    async def scenario() -> None:
        async with _real_services(monkeypatch) as (engine, factory, redis):
            student_id, session_id, resource_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
            notifications: list[tuple[uuid.UUID, uuid.UUID]] = []
            try:
                async with factory() as db:
                    db.add(_student(student_id, f"e2e-{student_id.hex[:8]}"))
                    db.add(CallSession(id=session_id, agora_channel_id=f"resource-{session_id}", student_id=student_id, flow_type=CallFlowType.RESOURCE_DIAGNOSTIC))
                    db.add(Resource(id=resource_id, skill_tag="dbms", format=ResourceFormat.VIDEO, pacing=ResourcePacing.LONG, price_tier=ResourcePriceTier.FREE, url=f"https://e2e.example.invalid/{resource_id}", title="E2E DBMS Deep Dive"))
                    await db.commit()

                async def capture_notification(requested_student_id, resource):
                    notifications.append((requested_student_id, resource.id))

                monkeypatch.setattr(resource_diagnostic_service, "send_resource_link", capture_notification)
                await resource_diagnostic_orchestrator.handle_resource_turn(session_id, "I want to learn DBMS")
                await resource_diagnostic_orchestrator.handle_resource_turn(session_id, "A long deep dive")
                result = await resource_diagnostic_orchestrator.handle_resource_turn(session_id, "Free video lessons")

                async with factory() as db:
                    recommendation = await db.scalar(select(ResourceRecommendation).where(ResourceRecommendation.session_id == session_id))
                assert result["complete"] is True
                assert recommendation is not None
                assert recommendation.student_id == student_id
                assert recommendation.resource_id == resource_id
                assert notifications == [(student_id, resource_id)]
            finally:
                await redis.delete(f"resource-diagnostic:session:{session_id}")
                async with engine.begin() as connection:
                    await connection.execute(delete(ResourceRecommendation).where(ResourceRecommendation.session_id == session_id))
                    await connection.execute(delete(Transcript).where(Transcript.call_session_id == session_id))
                    await connection.execute(delete(Resource).where(Resource.id == resource_id))
                    await connection.execute(delete(CallSession).where(CallSession.id == session_id))
                    await connection.execute(delete(Student).where(Student.id == student_id))

    asyncio.run(scenario())


def test_matchmaker_full_lifecycle_expires_and_purges_messages(monkeypatch) -> None:
    async def scenario() -> None:
        async with _real_services(monkeypatch) as (engine, factory, redis):
            student_a_id, student_b_id = uuid.uuid4(), uuid.uuid4()
            bridge_id = None
            try:
                async with factory() as db:
                    db.add_all([
                        _student(student_a_id, f"e2e-{student_a_id.hex[:8]}", tags=["robotics", "python"]),
                        _student(student_b_id, f"e2e-{student_b_id.hex[:8]}", tags=["robotics", "design"]),
                    ])
                    await db.commit()

                matched_id = await matchmaker_service.find_match(student_a_id, {"tags": ["robotics"]})
                assert matched_id == student_b_id
                bridge = await matchmaker_service.create_bridge(student_a_id, matched_id, "Shared robotics")
                bridge_id = bridge.id
                messages = await matchmaker_service.get_messages(bridge_id)
                assert messages and messages[0]["sender_id"] == "system"
                assert "robotics" in messages[0]["content"].lower()

                first_consent = await matchmaker_service.request_reveal(bridge_id, student_a_id)
                second_consent = await matchmaker_service.request_reveal(bridge_id, student_b_id)
                assert first_consent == {"status": "pending"}
                assert "linkedin_urls" not in first_consent
                assert second_consent["status"] == "revealed"
                assert set(second_consent["linkedin_urls"]) == {
                    f"https://linkedin.example.invalid/e2e-{student_a_id.hex[:8]}",
                    f"https://linkedin.example.invalid/e2e-{student_b_id.hex[:8]}",
                }

                future = datetime.now(timezone.utc) + timedelta(hours=49)

                class FutureDateTime(datetime):
                    @classmethod
                    def now(cls, tz=None):
                        return future if tz is not None else future.replace(tzinfo=None)

                monkeypatch.setattr(expiry_worker, "datetime", FutureDateTime)
                expired_count = await expiry_worker.expire_due_bridges()
                async with factory() as db:
                    stored_bridge = await db.get(ChatBridge, bridge_id)
                assert expired_count >= 1
                assert stored_bridge is not None and stored_bridge.status == BridgeStatus.EXPIRED
                assert await redis.exists(matchmaker_service.MESSAGE_KEY.format(bridge_id=bridge_id)) == 0
            finally:
                if bridge_id is not None:
                    await redis.delete(matchmaker_service.MESSAGE_KEY.format(bridge_id=bridge_id))
                async with engine.begin() as connection:
                    if bridge_id is not None:
                        await connection.execute(delete(ConsentReveal).where(ConsentReveal.bridge_id == bridge_id))
                        await connection.execute(delete(ChatBridge).where(ChatBridge.id == bridge_id))
                    await connection.execute(delete(Student).where(Student.id.in_((student_a_id, student_b_id))))

    asyncio.run(scenario())
