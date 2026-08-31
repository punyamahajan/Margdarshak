from app.api.v1.routes_dashboard import TelemetryResponse


def test_telemetry_schema_contains_aggregates_only() -> None:
    response = TelemetryResponse(
        bridge_status_counts={
            "active": 2,
            "expired": 1,
            "revealed": 1,
            "upgraded_to_voice": 0,
        },
        top_requested_skills=[{"skill": "python", "count": 3}],
    ).model_dump()

    serialized = str(response)
    forbidden = (
        "student_a_id",
        "student_b_id",
        "student_id",
        "roll_number",
        "linkedin_url",
        "email",
        "phone",
    )
    assert all(field not in serialized for field in forbidden)
