from app.services.admin_workflow_service import calculate_priority, classify_issue, issue_similarity


def test_issue_classifier_covers_admin_categories() -> None:
    assert classify_issue("assessment link is not working") == "Technical / Assessment"
    assert classify_issue("am I eligible with a backlog") == "Eligibility"
    assert classify_issue("when is my interview schedule") == "Interview"


def test_repeated_issue_similarity() -> None:
    assert issue_similarity("Riverbank assessment link not working", "assessment link is not opening") >= 0.35
    assert issue_similarity("assessment link failed", "eligibility CGPA requirement") < 0.35


def test_priority_uses_affected_urgency_deadline_and_blocking() -> None:
    score, level = calculate_priority(11, ["high"], blocked=True, deadline_days=0)
    assert score >= 70
    assert level == "critical"
