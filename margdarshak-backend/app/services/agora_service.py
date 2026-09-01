import time
import uuid
from typing import Any

import httpx

from app.core.config import get_settings


class AgoraServiceError(RuntimeError):
    """Raised when an Agora operation cannot be completed."""


def generate_rtc_token(channel_name: str, uid: int) -> str:
    """Generate a server-side RTC token without exposing the app certificate."""

    if not channel_name.strip():
        raise AgoraServiceError("channel_name must not be empty")
    if uid < 0:
        raise AgoraServiceError("uid must be non-negative")

    try:
        from agora_token_builder import RtcTokenBuilder
        from agora_token_builder.RtcTokenBuilder import Role_Attendee
    except ImportError as exc:
        raise AgoraServiceError("agora-token-builder is not installed") from exc

    settings = get_settings()
    expires_at = int(time.time()) + settings.agora_token_ttl_seconds

    try:
        return RtcTokenBuilder.buildTokenWithUid(
            settings.agora_app_id,
            settings.agora_app_certificate.get_secret_value(),
            channel_name,
            uid,
            Role_Attendee,
            expires_at,
        )
    except Exception as exc:
        raise AgoraServiceError("failed to generate Agora RTC token") from exc


def _convo_ai_auth() -> tuple[str, str]:
    settings = get_settings()
    customer_secret = settings.agora_customer_secret.get_secret_value()
    if not settings.agora_customer_id.strip() or not customer_secret:
        raise AgoraServiceError(
            "AGORA_CUSTOMER_ID and AGORA_CUSTOMER_SECRET are required to start the AI agent"
        )
    return settings.agora_customer_id, customer_secret


async def start_agent_session(channel_name: str, remote_uid: int) -> dict[str, Any]:
    """Start the configured Conversational AI agent on an RTC channel."""

    if not channel_name.strip():
        raise AgoraServiceError("channel_name must not be empty")

    settings = get_settings()
    if not settings.agora_ai_agent.strip():
        raise AgoraServiceError("AGORA_AI_AGENT is not configured")
    if not 0 < remote_uid < 2_147_483_647:
        raise AgoraServiceError("remote_uid must be between 1 and 2147483646")

    agent_uid = settings.agora_agent_rtc_uid
    if agent_uid == remote_uid:
        raise AgoraServiceError("AGORA_AGENT_RTC_UID must differ from the caller UID")

    # AGORA_AI_AGENT is the published Agent Studio pipeline ID. The runtime
    # agent ID is created by this request and is a different value.
    agent_token = generate_rtc_token(channel_name, agent_uid)
    request_body = {
        "name": f"margdarshak-{uuid.uuid4().hex}",
        "pipeline_id": settings.agora_ai_agent,
        "properties": {
            "channel": channel_name,
            "token": agent_token,
            "agent_rtc_uid": str(agent_uid),
            "remote_rtc_uids": [str(remote_uid)],
            "enable_string_uid": False,
            "idle_timeout": 120,
        },
    }
    url = (
        f"{settings.agora_convo_ai_base_url.rstrip('/')}/"
        f"{settings.agora_app_id}/join"
    )

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                url,
                json=request_body,
                auth=_convo_ai_auth(),
                headers={"Accept": "application/json"},
            )
        response.raise_for_status()
        result = response.json()
        if not result.get("agent_id"):
            raise AgoraServiceError("Agora started no agent: response omitted agent_id")
        result.setdefault("status", result.get("state", "started"))
        result.setdefault("channel_name", channel_name)
        return result
    except AgoraServiceError:
        raise
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise AgoraServiceError(
            f"Agora rejected the agent start request ({exc.response.status_code}): {detail}"
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise AgoraServiceError(
            f"failed to start Agora agent for channel {channel_name!r}"
        ) from exc


async def stop_agent_session(agent_id: str) -> None:
    """Remove a running Conversational AI agent from its RTC channel."""

    if not agent_id.strip():
        return
    settings = get_settings()
    url = (
        f"{settings.agora_convo_ai_base_url.rstrip('/')}/"
        f"{settings.agora_app_id}/agents/{agent_id}/leave"
    )
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, auth=_convo_ai_auth())
        # Treat an already-gone agent as successfully stopped.
        if response.status_code != 404:
            response.raise_for_status()
    except AgoraServiceError:
        raise
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise AgoraServiceError(
            f"Agora rejected the agent stop request ({exc.response.status_code}): {detail}"
        ) from exc
    except httpx.HTTPError as exc:
        raise AgoraServiceError("failed to stop Agora agent") from exc


async def handover_to_human(
    channel_name: str, poc_contact: str, summary: str
) -> dict[str, Any]:
    """Invite a human POC to the live channel with concise case context."""

    if not channel_name.strip():
        raise AgoraServiceError("channel_name must not be empty")
    if not poc_contact.strip():
        raise AgoraServiceError("poc_contact must not be empty")
    if not summary.strip():
        raise AgoraServiceError("case summary must not be empty")

    try:
        # TODO: Call Agora's human-handover/invite endpoint with the channel,
        # POC destination, agent identifier, and private case summary.
        return {
            "channel_name": channel_name,
            "poc_contact": poc_contact,
            "status": "handover_pending",
            "summary_delivered": True,
        }
    except Exception as exc:
        raise AgoraServiceError(
            f"failed to hand over channel {channel_name!r} to a human"
        ) from exc
