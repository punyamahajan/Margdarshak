import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.resource import Resource, ResourceRecommendation

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("/recommendations/{session_id}")
async def get_resource_recommendation(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    row = (
        await db.execute(
            select(ResourceRecommendation, Resource)
            .join(Resource, Resource.id == ResourceRecommendation.resource_id)
            .where(ResourceRecommendation.session_id == session_id)
            .order_by(ResourceRecommendation.created_at.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="resource recommendation not found")

    recommendation, resource = row
    return {
        "recommendation_id": recommendation.id,
        "student_id": recommendation.student_id,
        "session_id": recommendation.session_id,
        "reasoning_snapshot": recommendation.reasoning_snapshot,
        "created_at": recommendation.created_at,
        "resource": {
            "id": resource.id,
            "skill_tag": resource.skill_tag,
            "title": resource.title,
            "url": resource.url,
            "format": resource.format.value,
            "pacing": resource.pacing.value,
            "price_tier": resource.price_tier.value,
        },
    }
