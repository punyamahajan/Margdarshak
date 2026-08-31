import re
from typing import Any

CONFIDENCE_THRESHOLD = 0.90

_TIME_SENSITIVE_PATTERNS = (
    r"\blink (?:is )?not working\b",
    r"\btest (?:has )?expired\b",
    r"\bportal (?:is )?down\b",
    r"\bdeadline (?:is )?(?:today|tonight|tomorrow)\b",
    r"\bunable to (?:submit|apply|login|log in)\b",
)


def score_confidence(orchestrator_output: dict[str, Any]) -> float:
    """Score extraction completeness and routing evidence for one turn."""

    required_fields = ("classification", "next_action", "issue_summary")
    score = sum(bool(orchestrator_output.get(field)) for field in required_fields) * 0.25

    classification = orchestrator_output.get("classification")
    if classification == "policy_question":
        policy = orchestrator_output.get("policy") or {}
        exact_policy_match = bool(policy.get("id") and policy.get("policy_doc_ref"))
        score += 0.25 if exact_policy_match else 0.0
    elif classification == "grievance":
        routing_evidence = bool(orchestrator_output.get("message"))
        score += 0.25 if routing_evidence else 0.0

    # TODO: Replace this deterministic heuristic with a calibrated LLM scorer.
    return min(1.0, max(0.0, round(score, 2)))


def is_time_sensitive_grievance(transcript_chunk: str) -> bool:
    normalized = " ".join(transcript_chunk.lower().split())
    # TODO: Replace keyword matching with a context-aware urgency classifier.
    return any(re.search(pattern, normalized) for pattern in _TIME_SENSITIVE_PATTERNS)
