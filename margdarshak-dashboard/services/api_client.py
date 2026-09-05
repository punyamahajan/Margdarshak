import os
import uuid
from typing import Any

import requests
from dotenv import load_dotenv
from urllib.parse import urlsplit, urlunsplit

load_dotenv()


class APIClientError(RuntimeError):
    """Raised when the coordinator dashboard cannot read backend data."""


class ShortlistValidationError(APIClientError):
    """Raised when uploaded shortlist file is missing required columns (Section 67)."""
    def __init__(self, message: str, missing_columns: list[str] | None = None) -> None:
        super().__init__(message)
        self.missing_columns = missing_columns or []


class InvalidCSVError(APIClientError):
    """Raised when uploaded shortlist file is corrupt or invalid CSV/XLSX (Section 67)."""
    pass



def _base_url() -> str:
    value = os.getenv("MARGDARSHAK_API_URL", "http://127.0.0.1:8000/api/v1").strip().rstrip("/")
    if not value:
        value = "http://127.0.0.1:8000/api/v1"
    if not value.endswith("/api/v1"):
        value = f"{value}/api/v1"
    return value


def _admin_headers() -> dict[str, str]:
    token = os.getenv(
        "ADMIN_API_KEY",
        os.getenv("MARGDARSHAK_ADMIN_KEY", "local-admin-demo"),
    ).strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


def _request_json(
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise APIClientError(f"backend request failed: {exc}") from exc
    except ValueError as exc:
        raise APIClientError("backend returned invalid JSON") from exc


def _patch_json(
    url: str,
    *,
    body: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> Any:
    """Send a PATCH request with a JSON body and return the parsed response."""
    try:
        response = requests.patch(url, json=body, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise APIClientError(f"backend PATCH failed: {exc}") from exc
    except ValueError as exc:
        raise APIClientError("backend returned invalid JSON from PATCH") from exc


def _post_json(
    url: str,
    *,
    body: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> Any:
    """Send a POST request with a JSON body and return the parsed response."""
    try:
        response = requests.post(url, json=body, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise APIClientError(f"backend POST failed: {exc}") from exc
    except ValueError as exc:
        raise APIClientError("backend returned invalid JSON from POST") from exc


def _get(
    path: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    # This client intentionally exposes GET only. The dashboard never accesses
    # the database or sends mutations to the backend.
    return _request_json(f"{_base_url()}{path}", params=params, headers=headers)


def get_backend_health() -> dict[str, Any]:
    parsed = urlsplit(_base_url())
    health_url = urlunsplit((parsed.scheme, parsed.netloc, "/health", "", ""))
    payload = _request_json(health_url)
    if not isinstance(payload, dict):
        raise APIClientError("GET /health returned an unexpected response")
    return payload


def get_tickets(*, status: str | None = None) -> list[dict[str, Any]]:
    params = {"status": status} if status else None
    payload = _get("/tickets", params=params)
    if not isinstance(payload, list):
        raise APIClientError("GET /tickets returned an unexpected response")
    return payload


def get_ticket(ticket_id: str) -> dict[str, Any]:
    payload = _get(f"/tickets/{ticket_id}")
    if not isinstance(payload, dict):
        raise APIClientError("GET /tickets/{id} returned an unexpected response")
    return payload


def get_telemetry() -> dict[str, Any]:
    payload = _get("/dashboard/telemetry")
    if not isinstance(payload, dict):
        raise APIClientError(
            "GET /dashboard/telemetry returned an unexpected response"
        )
    return payload


def get_admin_overview() -> dict[str, Any]:
    """Retrieve operational metrics, priority tickets, active drives, and recent updates."""
    payload = _get("/admin/overview", headers=_admin_headers())
    if not isinstance(payload, dict):
        raise APIClientError("GET /admin/overview returned an unexpected response")
    return payload


def get_admin_clusters() -> list[dict[str, Any]]:
    """Retrieve repeated issue clusters with affected student counts and priority scores."""
    payload = _get("/admin/clusters", headers=_admin_headers())
    if not isinstance(payload, list):
        raise APIClientError("GET /admin/clusters returned an unexpected response")
    return payload


def get_admin_tickets(
    *,
    status: str | None = None,
    drive_id: str | None = None,
    company: str | None = None,
    round_name: str | None = None,
    coordinator: str | None = None,
    language: str | None = None,
    urgency: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve tickets enriched with coordinator workflow and intelligence."""
    params: dict[str, str] = {}
    if status:
        params["status"] = status
    if drive_id and drive_id.strip():
        # Validate drive_id is a valid UUID before sending as query param
        try:
            uuid.UUID(drive_id.strip())
            params["drive_id"] = drive_id.strip()
        except (ValueError, AttributeError):
            pass
    if company and company.strip():
        params["company"] = company.strip()
    if round_name and round_name.strip():
        params["round_name"] = round_name.strip()
    if coordinator and coordinator.strip():
        params["coordinator"] = coordinator.strip()
    if language and language.strip():
        params["language"] = language.strip()
    if urgency and urgency.strip():
        params["urgency"] = urgency.strip()

    payload = _get("/admin/tickets", params=params or None, headers=_admin_headers())
    if not isinstance(payload, list):
        raise APIClientError("GET /admin/tickets returned an unexpected response")
    return payload


def get_admin_stats() -> dict[str, Any]:
    """Retrieve operational coordinator statistics and distribution data."""
    payload = _get("/admin/stats", headers=_admin_headers())
    if not isinstance(payload, dict):
        raise APIClientError("GET /admin/stats returned an unexpected response")
    return payload


def get_admin_ticket(ticket_id: str) -> dict[str, Any]:
    """Fetch full ticket detail (including case card) from GET /admin/tickets enriched response.

    Falls back to the public GET /tickets/{id} endpoint which includes the case_card.
    The public endpoint doesn't require coordinator auth; it is acceptable for read-only detail.
    """
    payload = _get(f"/tickets/{ticket_id}")
    if not isinstance(payload, dict):
        raise APIClientError(f"GET /tickets/{ticket_id} returned an unexpected response")
    return payload


def patch_admin_ticket(
    ticket_id: str,
    *,
    status: str | None = None,
    assigned_coordinator: str | None = None,
    urgency: str | None = None,
    language: str | None = None,
    category: str | None = None,
    original_request: str | None = None,
    conversation_summary: str | None = None,
) -> dict[str, Any]:
    """Send a coordinator workflow update via PATCH /api/v1/admin/tickets/{id}.

    Maps to WorkflowUpdate in routes_admin.py. Only non-None fields are sent.
    Lifecycle (§44): OPEN → CLAIMED → WAITING / ESCALATED → RESOLVED.

    Action transitions:
    - Claim:    status="claimed"
    - Escalate: status="escalated"
    - Resolve:  status="resolved"
    - Dismiss:  status="resolved" + conversation_summary noting dismissal
    """
    body: dict[str, Any] = {}
    if status is not None:
        body["status"] = status
    if assigned_coordinator is not None:
        body["assigned_coordinator"] = assigned_coordinator
    if urgency is not None:
        body["urgency"] = urgency
    if language is not None:
        body["language"] = language
    if category is not None:
        body["category"] = category
    if original_request is not None:
        body["original_request"] = original_request
    if conversation_summary is not None:
        body["conversation_summary"] = conversation_summary

    result = _patch_json(
        f"{_base_url()}/admin/tickets/{ticket_id}",
        body=body,
        headers=_admin_headers(),
    )
    if not isinstance(result, dict):
        raise APIClientError(f"PATCH /admin/tickets/{ticket_id} returned an unexpected response")
    return result



def get_admin_clusters() -> list[dict[str, Any]]:
    """Fetch all ticket clusters from GET /api/v1/admin/clusters.

    Each cluster payload (from routes_admin.py:list_clusters) includes:
        id, title, company_name, urgency (priority label), priority_score,
        status, affected_students, incident_update, response_draft, created_at.

    Priority is calculated server-side by calculate_priority() using:
        affected_students, individual ticket urgency, deadline proximity,
        frequency, and whether students are blocked (§37).

    NOTE: GET /admin/clusters/{id} does NOT exist server-side.
    Single-cluster lookups are handled by filtering this list client-side.
    """
    payload = _get("/admin/clusters", headers=_admin_headers())
    if not isinstance(payload, list):
        raise APIClientError("GET /admin/clusters returned an unexpected response")
    return payload


def post_admin_agora_session() -> dict[str, Any]:
    """Issue a short-lived RTC credential for coordinator voice drafting.

    Calls POST /api/v1/admin/agora/session.
    Returns: { "app_id", "channel_name", "uid", "rtc_token" }
    """
    result = _post_json(
        f"{_base_url()}/admin/agora/session",
        body={},
        headers=_admin_headers(),
    )
    if not isinstance(result, dict):
        raise APIClientError("POST /admin/agora/session returned an unexpected response")
    return result


def post_cluster_draft_response(cluster_id: str, *, notes: str) -> dict[str, Any]:
    """Draft a response for a cluster using AI.

    Calls POST /api/v1/admin/clusters/{id}/draft-response.
    Body: { "notes": str }  — maps to DraftWrite in routes_admin.py.
    """
    result = _post_json(
        f"{_base_url()}/admin/clusters/{cluster_id}/draft-response",
        body={"notes": notes},
        headers=_admin_headers(),
    )
    if not isinstance(result, dict):
        raise APIClientError(f"POST /admin/clusters/{cluster_id}/draft-response returned an unexpected response")
    return result



def post_cluster_publish_update(cluster_id: str, *, message: str) -> dict[str, Any]:
    """Publish a coordinator incident update to all affected students.

    Calls POST /api/v1/admin/clusters/{id}/publish-update.
    Body: { "message": str }  — maps to UpdateWrite in routes_admin.py.

    Side effects (server-side):
    - Sets cluster.incident_update = message
    - Creates StudentNotification rows for every student in the cluster
    """
    result = _post_json(
        f"{_base_url()}/admin/clusters/{cluster_id}/publish-update",
        body={"message": message},
        headers=_admin_headers(),
    )
    if not isinstance(result, dict):
        raise APIClientError(f"POST /admin/clusters/{cluster_id}/publish-update returned an unexpected response")
    return result


def post_cluster_resolve(cluster_id: str) -> dict[str, Any]:
    """Resolve a cluster and bulk-resolve all associated tickets.

    Calls POST /api/v1/admin/clusters/{id}/resolve.
    Side effects (server-side):
    - Sets cluster.status = "resolved"
    - Sets all linked TicketWorkflow.status = "resolved"
    - Creates a KnowledgeDocument of type "resolved_issue" (§42 Resolution Memory)
    """
    result = _post_json(
        f"{_base_url()}/admin/clusters/{cluster_id}/resolve",
        body={},
        headers=_admin_headers(),
    )
    if not isinstance(result, dict):
        raise APIClientError(f"POST /admin/clusters/{cluster_id}/resolve returned an unexpected response")
    return result


def get_knowledge() -> list[dict[str, Any]]:
    """Retrieve all knowledge documents from GET /api/v1/knowledge (or /admin/knowledge).

    Each document payload includes:
        id, title, type, company, version, status, source, content, created_at.
    """
    try:
        payload = _get("/knowledge", headers=_admin_headers())
    except APIClientError:
        payload = _get("/admin/knowledge", headers=_admin_headers())
    if not isinstance(payload, list):
        raise APIClientError("GET /knowledge returned an unexpected response")
    return payload


def post_knowledge_policy(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a new policy knowledge document draft or published item.

    Calls POST /api/v1/knowledge/policy (or /api/v1/admin/knowledge/policy).
    Accepts:
        title: str (Source Title)
        document_type: str ("placement_policy")
        company_name: str | None
        drive_id: uuid.UUID | None
        version_label: str (e.g. "2026.1")
        source_reference: str (e.g. "manual://coordinator-entry")
        status: str ("draft" or "published")
        content: dict (eligibility, salary_ctc, deadline, application_url, instructions)
    """
    try:
        result = _post_json(
            f"{_base_url()}/knowledge/policy",
            body=payload,
            headers=_admin_headers(),
        )
    except APIClientError:
        result = _post_json(
            f"{_base_url()}/admin/knowledge",
            body=payload,
            headers=_admin_headers(),
        )
    if not isinstance(result, dict):
        raise APIClientError("POST /knowledge/policy returned an unexpected response")
    return result


def patch_knowledge_status(document_id: str, status: str) -> dict[str, Any]:
    """Update a knowledge document's status lifecycle (draft, published, expired).

    Calls PATCH /api/v1/knowledge/{id}?status={status} (or /admin/knowledge/{id}).
    """
    try:
        result = _patch_json(
            f"{_base_url()}/knowledge/{document_id}?status={status}",
            body={"status": status},
            headers=_admin_headers(),
        )
    except APIClientError:
        result = _patch_json(
            f"{_base_url()}/admin/knowledge/{document_id}?status={status}",
            body={"status": status},
            headers=_admin_headers(),
        )
    if not isinstance(result, dict):
        raise APIClientError(f"PATCH /knowledge/{document_id} returned an unexpected response")
    return result


def preview_shortlist(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """Upload and preview a CSV or XLSX shortlist before confirmation.

    Calls POST /api/v1/knowledge/shortlist-preview (or /preview).
    Raises:
        InvalidCSVError: On unreadable/corrupt files or invalid format (Section 67).
        ShortlistValidationError: When required columns are missing (Section 67).
        APIClientError: On network or server errors.
    """
    url = f"{_base_url()}/knowledge/shortlist-preview"
    headers = _admin_headers()
    files = {"file": (filename, file_bytes)}
    try:
        response = requests.post(url, files=files, headers=headers, timeout=20)
        if response.status_code == 404:
            url = f"{_base_url()}/admin/knowledge/shortlist-preview"
            response = requests.post(url, files=files, headers=headers, timeout=20)

        if response.status_code == 422:
            try:
                err_data = response.json().get("detail", {})
                if isinstance(err_data, dict):
                    missing = err_data.get("columns", [])
                    msg = err_data.get("message", "missing required shortlist columns")
                else:
                    missing = []
                    msg = str(err_data)
            except Exception:
                missing = []
                msg = response.text
            raise ShortlistValidationError(
                f"Missing required fields: {msg}",
                missing_columns=missing,
            )

        if response.status_code in {400, 415}:
            try:
                detail = response.json().get("detail", "invalid file format")
            except Exception:
                detail = response.text
            raise InvalidCSVError(f"Invalid CSV: {detail}")

        response.raise_for_status()
        return response.json()
    except (ShortlistValidationError, InvalidCSVError):
        raise
    except requests.RequestException as exc:
        raise APIClientError(f"backend request failed: {exc}") from exc
    except ValueError as exc:
        raise APIClientError("backend returned invalid JSON from shortlist preview") from exc


def import_shortlist(payload: dict[str, Any]) -> dict[str, Any]:
    """Confirm and persist a validated shortlist import.

    Calls POST /api/v1/knowledge/import (or /admin/knowledge/shortlist-import).
    Payload:
        title: str
        source_reference: str
        version_label: str
        rows: list[dict[str, Any]]
    Returns:
        {"document_id": str, "imported": int, "status": "published"}
    """
    try:
        result = _post_json(
            f"{_base_url()}/knowledge/import",
            body=payload,
            headers=_admin_headers(),
        )
    except APIClientError:
        result = _post_json(
            f"{_base_url()}/admin/knowledge/shortlist-import",
            body=payload,
            headers=_admin_headers(),
        )
    if not isinstance(result, dict):
        raise APIClientError("POST /knowledge/import returned an unexpected response")
    return result


def get_stats() -> dict[str, Any]:
    """Retrieve operational coordinator statistics from GET /api/v1/stats (or /admin/stats).

    Returns 8 spec metrics (§45):
        total_conversations: int
        tickets_created: int
        tickets_resolved: int
        students_assisted: int
        average_resolution_time_hours: float
        most_common_issue_categories: dict[str, int]
        most_requested_companies: dict[str, int]
        most_common_languages: dict[str, int]
    """
    try:
        payload = _get("/stats", headers=_admin_headers())
    except APIClientError:
        payload = _get("/admin/stats", headers=_admin_headers())
    if not isinstance(payload, dict):
        raise APIClientError("GET /stats returned an unexpected response")
    return payload



