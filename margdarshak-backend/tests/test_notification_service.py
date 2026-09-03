import asyncio
import uuid

from app.models.resource import (
    Resource,
    ResourceFormat,
    ResourcePacing,
    ResourcePriceTier,
)
from app.services.notification_service import send_resource_link


def test_resource_notification_does_not_use_reserved_log_fields() -> None:
    resource = Resource(
        id=uuid.uuid4(),
        skill_tag="web_dev",
        format=ResourceFormat.SHEET,
        pacing=ResourcePacing.SHORT,
        price_tier=ResourcePriceTier.FREE,
        url="https://example.invalid/course",
        title="Example course",
    )

    asyncio.run(send_resource_link(uuid.uuid4(), resource))
