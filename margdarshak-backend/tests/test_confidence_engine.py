from app.services.confidence_engine import (
    CONFIDENCE_THRESHOLD,
    is_time_sensitive_grievance,
    score_confidence,
)


def test_exact_policy_match_scores_above_threshold() -> None:
    output = {
        "classification": "policy_question",
        "next_action": "answer_from_drive_policy",
        "issue_summary": "What is the eligibility policy?",
        "policy": {"id": "drive-id", "policy_doc_ref": "policy/ref"},
    }

    assert score_confidence(output) >= CONFIDENCE_THRESHOLD


def test_incomplete_policy_lookup_scores_below_threshold() -> None:
    output = {
        "classification": "policy_question",
        "next_action": "request_drive_id",
        "issue_summary": "What is the policy?",
    }

    assert score_confidence(output) < CONFIDENCE_THRESHOLD


def test_time_sensitive_grievance_patterns() -> None:
    assert is_time_sensitive_grievance("The application link is not working")
    assert is_time_sensitive_grievance("Our placement portal is down")
    assert is_time_sensitive_grievance("This is urgent, I can't apply right now")
    assert not is_time_sensitive_grievance("I have a general interview concern")
