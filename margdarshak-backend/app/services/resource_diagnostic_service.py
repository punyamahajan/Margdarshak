import re
import uuid
from collections.abc import Sequence
from typing import Any, TypedDict

from sqlalchemy import select

from app.db.session_factory import get_session_factory
from app.models.resource import (
    Resource,
    ResourceFormat,
    ResourcePacing,
    ResourcePriceTier,
    ResourceRecommendation,
)
from app.services.notification_service import send_resource_link


class DiagnosticCriteria(TypedDict):
    skill: str | None
    pacing: str | None
    format: str | None
    budget: str | None


def extract_criteria(
    transcript_history: Sequence[str | dict[str, Any]],
) -> DiagnosticCriteria:
    """Extract normalized diagnostic criteria from all conversation turns.

    The stable return shape is::

        {"skill": str | None, "pacing": "short" | "long" | None,
         "format": "sheet" | "video" | None,
         "budget": "free" | "paid" | None}

    TODO: Replace these deterministic phrase rules with a structured-output LLM
    call that returns exactly ``DiagnosticCriteria`` and validates enum values.
    """

    parts = [
        str(turn.get("content", ""))
        for turn in transcript_history
        if isinstance(turn, dict) and turn.get("speaker") == "student"
    ]
    parts.extend(str(turn) for turn in transcript_history if isinstance(turn, str))
    text = " ".join(parts).lower()

    skill: str | None = None
    skill_patterns = (
        ("system_design", r"\bsystem\s+design\b|\bdistributed\s+systems?\b"),
        ("web_dev", r"\bweb\s+(?:dev|development)\b|\bfrontend\b|\bfull[ -]?stack\b"),
        ("dbms", r"\bdbms\b|\bdatabase(?:s)?\b|\bsql\b"),
        ("os", r"\boperating\s+systems?\b|\bos\s+(?:course|concepts?|study)\b"),
        ("dsa", r"\bdsa\b|\bdata\s+structures?\b|\balgorithms?\b"),
    )
    for normalized_skill, pattern in skill_patterns:
        if re.search(pattern, text):
            skill = normalized_skill
            break

    pacing: str | None = None
    if re.search(r"\b(short|quick|crash|rapid|concise|revision)\b", text):
        pacing = "short"
    elif re.search(r"\b(long|deep[ -]?dive|detailed|comprehensive|in[ -]?depth)\b", text):
        pacing = "long"

    resource_format: str | None = None
    if re.search(r"\b(sheet|hands[ -]?on|practice|problems?|exercises?)\b", text):
        resource_format = "sheet"
    elif re.search(r"\b(videos?|watch|lectures?|playlists?)\b", text):
        resource_format = "video"

    budget: str | None = None
    if re.search(r"\b(free|no[ -]?cost|zero[ -]?cost)\b", text):
        budget = "free"
    elif re.search(r"\b(paid|premium|subscription|paying)\b", text):
        budget = "paid"

    return {
        "skill": skill,
        "pacing": pacing,
        "format": resource_format,
        "budget": budget,
    }


def _normalize_criteria(criteria: dict[str, Any]) -> dict[str, str]:
    normalized = {
        "skill_tag": criteria.get("skill_tag") or criteria.get("skill"),
        "pacing": criteria.get("pacing"),
        "format": criteria.get("format"),
        "price_tier": criteria.get("price_tier") or criteria.get("budget"),
    }
    if not all(normalized.values()):
        raise ValueError("skill, pacing, format, and price tier are required")
    normalized["pacing"] = ResourcePacing(str(normalized["pacing"])).value
    normalized["format"] = ResourceFormat(str(normalized["format"])).value
    normalized["price_tier"] = ResourcePriceTier(str(normalized["price_tier"])).value
    return {key: str(value) for key, value in normalized.items()}


async def _find_with_relaxations(
    db: Any, criteria: dict[str, Any]
) -> tuple[Resource, list[str]]:
    requested = _normalize_criteria(criteria)
    filters = dict(requested)
    relaxed: list[str] = []

    # Relax cumulatively in this deliberate order: price, format, then pacing.
    for criterion_to_relax in (None, "price_tier", "format", "pacing"):
        if criterion_to_relax is not None:
            filters.pop(criterion_to_relax)
            relaxed.append(criterion_to_relax)

        statement = select(Resource).where(Resource.skill_tag == filters["skill_tag"])
        if "pacing" in filters:
            statement = statement.where(Resource.pacing == filters["pacing"])
        if "format" in filters:
            statement = statement.where(Resource.format == filters["format"])
        if "price_tier" in filters:
            statement = statement.where(Resource.price_tier == filters["price_tier"])
        resource = (await db.scalars(statement.order_by(Resource.title, Resource.id))).first()
        if resource is not None:
            return resource, relaxed

    raise ValueError(
        f"no resources are available for skill {requested['skill_tag']!r}"
    )


async def find_best_resource(criteria: dict[str, Any]) -> Resource:
    """Find an exact resource or relax price, format, then pacing."""

    async with get_session_factory()() as db:
        resource, _ = await _find_with_relaxations(db, criteria)
        return resource


async def recommend(
    student_id: uuid.UUID, session_id: uuid.UUID, criteria: dict[str, Any]
) -> Resource:
    """Persist an auditable recommendation and deliver its link."""

    requested = _normalize_criteria(criteria)
    async with get_session_factory()() as db:
        async with db.begin():
            resource, relaxed = await _find_with_relaxations(db, requested)
            relaxation_note = (
                "No criteria were relaxed."
                if not relaxed
                else f"Relaxed criteria in order: {', '.join(relaxed)}."
            )
            reasoning = (
                f"Requested skill={requested['skill_tag']}, "
                f"pacing={requested['pacing']}, format={requested['format']}, "
                f"price_tier={requested['price_tier']}. {relaxation_note}"
            )
            db.add(
                ResourceRecommendation(
                    student_id=student_id,
                    resource_id=resource.id,
                    session_id=session_id,
                    reasoning_snapshot=reasoning,
                )
            )
            await db.flush()

    await send_resource_link(student_id, resource)
    return resource
