import logging
import uuid

from app.models.resource import Resource

logger = logging.getLogger(__name__)


async def send_resource_link(student_id: uuid.UUID, resource: Resource) -> None:
    """Log the text payload at the future SMS-provider boundary."""

    message = (
        f"{resource.title}\n{resource.url}\n"
        f"Format: {resource.format.value}\nPrice: {resource.price_tier.value}"
    )
    # TODO: Resolve the student's phone and send `message` with Twilio or another
    # transactional SMS provider. Never log the student's phone number.
    logger.info(
        "resource_link_sms_stub",
        extra={
            "student_id": str(student_id),
            "resource_id": str(resource.id),
            # `message` is a reserved LogRecord attribute and raises KeyError
            # when supplied through `extra`.
            "notification_text": message,
            "delivery_status": "not_sent_stub",
        },
    )
