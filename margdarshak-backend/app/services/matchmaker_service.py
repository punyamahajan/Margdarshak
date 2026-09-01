import json
import uuid
from math import ceil
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from app.db.session_factory import get_session_factory
from app.db.redis import get_redis_client
from app.models.chat_bridge import BridgeStatus, ChatBridge
from app.models.consent_reveal import ConsentPurpose, ConsentReveal
from app.models.student import Student
from app.services.agora_service import generate_rtc_token

BRIDGE_DURATION = timedelta(hours=48)
MESSAGE_KEY = "chatbridge:{bridge_id}:messages"


class MatchmakerError(RuntimeError):
    pass


def _icebreaker_prompt(
    student_a_context: dict[str, Any], student_b_context: dict[str, Any]
) -> str:
    return f"""You write opening messages for an anonymous campus peer chat.
Write one warm, specific message of at most 45 words that explains what the
two students have in common and ends with one easy conversation question.
Never mention names, roll numbers, email addresses, phone numbers, or infer
identity. Do not use generic phrases like 'You have been matched'.

Student A interests/responsibilities: {student_a_context.get('tags', [])}
Student B interests/responsibilities: {student_b_context.get('tags', [])}
Match reason: {student_a_context.get('match_reason') or student_b_context.get('match_reason')}
"""


def generate_icebreaker(
    student_a_context: dict[str, Any], student_b_context: dict[str, Any]
) -> str:
    """Produce a deterministic icebreaker at the future LLM call boundary."""

    prompt = _icebreaker_prompt(student_a_context, student_b_context)
    # TODO: Send `prompt` to the configured LLM and validate its safety/length.
    del prompt

    a_tags = {str(tag).strip() for tag in student_a_context.get("tags", []) if tag}
    b_tags = {str(tag).strip() for tag in student_b_context.get("tags", []) if tag}
    common = sorted(a_tags.intersection(b_tags), key=str.lower)
    reason = student_a_context.get("match_reason") or student_b_context.get(
        "match_reason"
    )
    shared_context = ", ".join(common) if common else str(reason or "campus work")
    return (
        f"You both care about {shared_context}. What are you working on right now "
        "that you would most enjoy comparing notes on?"
    )


async def _get_active_bridge(bridge_id: uuid.UUID) -> ChatBridge:
    async with get_session_factory()() as db:
        bridge = await db.get(ChatBridge, bridge_id)
        if bridge is None:
            raise MatchmakerError(f"bridge {bridge_id} does not exist")
        now = datetime.now(timezone.utc)
        if bridge.status != BridgeStatus.ACTIVE or bridge.expires_at <= now:
            raise MatchmakerError("bridge is no longer active")
        return bridge


async def add_message(
    bridge_id: uuid.UUID, sender_id: uuid.UUID | str, content: str
) -> dict[str, Any]:
    """Append an ephemeral message without extending the bridge lifetime."""

    normalized_content = content.strip()
    if not normalized_content:
        raise MatchmakerError("message content must not be empty")

    bridge = await _get_active_bridge(bridge_id)
    remaining_seconds = ceil(
        (bridge.expires_at - datetime.now(timezone.utc)).total_seconds()
    )
    if remaining_seconds <= 0:
        raise MatchmakerError("bridge is no longer active")

    message = {
        "sender_id": str(sender_id),
        "content": normalized_content,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    key = MESSAGE_KEY.format(bridge_id=bridge_id)
    redis = get_redis_client()
    await redis.rpush(key, json.dumps(message))
    current_ttl = await redis.ttl(key)
    if current_ttl < 0 or current_ttl > remaining_seconds:
        await redis.expire(key, remaining_seconds)
    return message


async def get_messages(bridge_id: uuid.UUID) -> list[dict[str, Any]]:
    key = MESSAGE_KEY.format(bridge_id=bridge_id)
    encoded_messages = await get_redis_client().lrange(key, 0, -1)
    messages: list[dict[str, Any]] = []
    for encoded in encoded_messages:
        if isinstance(encoded, bytes):
            encoded = encoded.decode("utf-8")
        messages.append(json.loads(encoded))
    return messages


def _normalized_criteria(criteria: dict[str, Any]) -> set[str]:
    values: list[str] = []
    for key in ("tags", "tech_stack_tags"):
        raw_tags = criteria.get(key, [])
        if isinstance(raw_tags, list):
            values.extend(str(tag) for tag in raw_tags)

    for key in ("campus_responsibility", "responsibility"):
        responsibility = criteria.get(key)
        if responsibility:
            values.append(str(responsibility))

    return {" ".join(value.lower().split()) for value in values if value.strip()}


async def opt_in_student(student_id: uuid.UUID, criteria: dict[str, Any]) -> set[str]:
    """Persist normalized matching preferences for the requesting student."""

    normalized_tags = _normalized_criteria(criteria)
    if not normalized_tags:
        raise MatchmakerError("at least one tag or campus responsibility is required")

    async with get_session_factory()() as db:
        async with db.begin():
            student = await db.get(Student, student_id, with_for_update=True)
            if student is None:
                raise MatchmakerError(f"student {student_id} does not exist")
            student.tags = sorted(normalized_tags)
            student.matchmaking_opt_in = True
    return normalized_tags


async def find_match(
    student_id: uuid.UUID, criteria: dict[str, Any]
) -> uuid.UUID | None:
    """Find the opted-in student with the highest preference overlap."""

    requested_tags = _normalized_criteria(criteria)
    if not requested_tags:
        return None

    statement = select(Student).where(
        Student.id != student_id,
        Student.matchmaking_opt_in.is_(True),
    )
    async with get_session_factory()() as db:
        candidates = (await db.scalars(statement)).all()

    scored_candidates: list[tuple[int, str, uuid.UUID]] = []
    for candidate in candidates:
        candidate_tags = {
            " ".join(tag.lower().split()) for tag in (candidate.tags or []) if tag.strip()
        }
        overlap_score = len(requested_tags.intersection(candidate_tags))
        if overlap_score:
            scored_candidates.append((overlap_score, str(candidate.id), candidate.id))

    if not scored_candidates:
        return None
    scored_candidates.sort(key=lambda item: (-item[0], item[1]))
    return scored_candidates[0][2]


async def create_bridge(
    student_a_id: uuid.UUID,
    student_b_id: uuid.UUID,
    match_reason: str,
) -> ChatBridge:
    if student_a_id == student_b_id:
        raise MatchmakerError("a student cannot be matched with themselves")

    created_at = datetime.now(timezone.utc)
    async with get_session_factory()() as db:
        student_a = await db.get(Student, student_a_id)
        student_b = await db.get(Student, student_b_id)
        if student_a is None or student_b is None:
            raise MatchmakerError("both bridge participants must exist")
        bridge = ChatBridge(
            student_a_id=student_a_id,
            student_b_id=student_b_id,
            match_reason=match_reason,
            created_at=created_at,
            expires_at=created_at + BRIDGE_DURATION,
            status=BridgeStatus.ACTIVE,
        )
        db.add(bridge)
        await db.commit()

    icebreaker = generate_icebreaker(
        {"tags": student_a.tags or [], "match_reason": match_reason},
        {"tags": student_b.tags or [], "match_reason": match_reason},
    )
    await add_message(bridge.id, "system", icebreaker)
    return bridge


async def _record_dual_consent(
    db: Any,
    bridge: ChatBridge,
    student_id: uuid.UUID,
    purpose: ConsentPurpose,
) -> bool:
    if student_id not in (bridge.student_a_id, bridge.student_b_id):
        raise MatchmakerError("student is not a participant in this bridge")

    existing = await db.scalar(
        select(ConsentReveal).where(
            ConsentReveal.bridge_id == bridge.id,
            ConsentReveal.student_id == student_id,
            ConsentReveal.consent_purpose == purpose,
        )
    )
    if existing is None:
        db.add(
            ConsentReveal(
                bridge_id=bridge.id,
                student_id=student_id,
                consent_purpose=purpose,
            )
        )
        await db.flush()

    consenting_students = set(
        (
            await db.scalars(
                select(ConsentReveal.student_id).where(
                    ConsentReveal.bridge_id == bridge.id,
                    ConsentReveal.consent_purpose == purpose,
                )
            )
        ).all()
    )
    return {bridge.student_a_id, bridge.student_b_id}.issubset(consenting_students)


async def request_reveal(
    bridge_id: uuid.UUID, student_id: uuid.UUID
) -> dict[str, Any]:
    """Record reveal consent and expose LinkedIn URLs only after dual consent."""

    async with get_session_factory()() as db:
        async with db.begin():
            bridge = await db.scalar(
                select(ChatBridge)
                .where(ChatBridge.id == bridge_id)
                .with_for_update()
            )
            if bridge is None:
                raise MatchmakerError(f"bridge {bridge_id} does not exist")
            if student_id not in (bridge.student_a_id, bridge.student_b_id):
                raise MatchmakerError("student is not a participant in this bridge")
            if bridge.status == BridgeStatus.REVEALED:
                student_a = await db.get(Student, bridge.student_a_id)
                student_b = await db.get(Student, bridge.student_b_id)
                if student_a is None or student_b is None:
                    raise MatchmakerError("bridge participant no longer exists")
                return {
                    "status": "revealed",
                    "linkedin_urls": [student_a.linkedin_url, student_b.linkedin_url],
                }
            if (
                bridge.status != BridgeStatus.ACTIVE
                or bridge.expires_at <= datetime.now(timezone.utc)
            ):
                raise MatchmakerError("bridge is not active")

            both_consented = await _record_dual_consent(
                db, bridge, student_id, ConsentPurpose.REVEAL
            )
            if not both_consented:
                return {"status": "pending"}

            student_a = await db.get(Student, bridge.student_a_id)
            student_b = await db.get(Student, bridge.student_b_id)
            if student_a is None or student_b is None:
                raise MatchmakerError("bridge participant no longer exists")
            bridge.status = BridgeStatus.REVEALED
            linkedin_urls = [student_a.linkedin_url, student_b.linkedin_url]

    return {"status": "revealed", "linkedin_urls": linkedin_urls}


def _agora_uid(student_id: uuid.UUID) -> int:
    return (student_id.int % 2_147_483_646) + 1


async def request_voice_upgrade(
    bridge_id: uuid.UUID, student_id: uuid.UUID
) -> dict[str, Any]:
    """Provision anonymous peer voice access only after dual consent."""

    async with get_session_factory()() as db:
        async with db.begin():
            bridge = await db.scalar(
                select(ChatBridge)
                .where(ChatBridge.id == bridge_id)
                .with_for_update()
            )
            if bridge is None:
                raise MatchmakerError(f"bridge {bridge_id} does not exist")
            if bridge.status not in (BridgeStatus.ACTIVE, BridgeStatus.REVEALED):
                raise MatchmakerError("bridge cannot be upgraded to voice")
            if bridge.expires_at <= datetime.now(timezone.utc):
                raise MatchmakerError("bridge has expired")

            both_consented = await _record_dual_consent(
                db, bridge, student_id, ConsentPurpose.VOICE_UPGRADE
            )
            if not both_consented:
                return {"status": "pending"}

            channel_name = f"matchmaker-{bridge.id.hex}-{uuid.uuid4().hex[:8]}"
            tokens = [
                generate_rtc_token(channel_name, _agora_uid(bridge.student_a_id)),
                generate_rtc_token(channel_name, _agora_uid(bridge.student_b_id)),
            ]
            bridge.status = BridgeStatus.UPGRADED_TO_VOICE

    return {
        "status": "upgraded_to_voice",
        "channel_name": channel_name,
        "rtc_tokens": tokens,
    }
