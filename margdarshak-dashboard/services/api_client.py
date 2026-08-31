import os
from typing import Any

import requests
from dotenv import load_dotenv
from urllib.parse import urlsplit, urlunsplit

load_dotenv()


class APIClientError(RuntimeError):
    """Raised when the coordinator dashboard cannot read backend data."""


def _base_url() -> str:
    value = os.getenv("MARGDARSHAK_API_URL", "").strip().rstrip("/")
    if not value:
        raise APIClientError("MARGDARSHAK_API_URL is not configured")
    return value


def _request_json(url: str, *, params: dict[str, str] | None = None) -> Any:
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise APIClientError(f"backend request failed: {exc}") from exc
    except ValueError as exc:
        raise APIClientError("backend returned invalid JSON") from exc


def _get(path: str, *, params: dict[str, str] | None = None) -> Any:
    # This client intentionally exposes GET only. The dashboard never accesses
    # the database or sends mutations to the backend.
    return _request_json(f"{_base_url()}{path}", params=params)


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
