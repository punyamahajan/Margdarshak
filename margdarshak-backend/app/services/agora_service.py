import time
from typing import Any

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
            RtcTokenBuilder.Role_Attendee,
            expires_at,
        )
    except Exception as exc:
        raise AgoraServiceError("failed to generate Agora RTC token") from exc


async def start_agent_session(channel_name: str) -> dict[str, Any]:
    """Start the configured Conversational AI agent on an RTC channel."""

    if not channel_name.strip():
        raise AgoraServiceError("channel_name must not be empty")

    settings = get_settings()
    if not settings.agora_ai_agent.strip():
        raise AgoraServiceError("AGORA_AI_AGENT is not configured")

    try:
        # TODO: Replace this stub with Agora's Conversational AI agent-start API
        # once the account-specific endpoint and authentication contract are set.
        return {
            "agent_id": settings.agora_ai_agent,
            "channel_name": channel_name,
            "status": "start_pending",
        }
    except Exception as exc:
        raise AgoraServiceError(
            f"failed to start Agora agent for channel {channel_name!r}"
        ) from exc


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
