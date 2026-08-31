import uuid
from datetime import datetime, timedelta, timezone

from app.api.v1.routes_matchmaker import AnonymousBridgeResponse
from app.models.chat_bridge import BridgeStatus


def test_bridge_response_contains_no_student_identity_fields() -> None:
    now = datetime.now(timezone.utc)
    response = AnonymousBridgeResponse(
        matched=True,
        bridge_id=uuid.uuid4(),
        status=BridgeStatus.ACTIVE,
        created_at=now,
        expires_at=now + timedelta(hours=48),
    ).model_dump()

    forbidden_fields = {
        "student_a_id",
        "student_b_id",
        "student_id",
        "name",
        "email",
        "roll_number",
        "phone",
    }
    assert forbidden_fields.isdisjoint(response)
