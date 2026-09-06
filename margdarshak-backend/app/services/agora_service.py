import time
import uuid
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.agora_token007 import build_rtc_rtm_token


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


def generate_rtc_rtm_token(channel_name: str, uid: int) -> str:
    """Generate the current multi-service token used by RTC and RTM."""

    settings = get_settings()
    expires_at = int(time.time()) + settings.agora_token_ttl_seconds
    try:
        return build_rtc_rtm_token(
            settings.agora_app_id,
            settings.agora_app_certificate.get_secret_value(),
            channel_name,
            str(uid),
            expires_at,
        )
    except Exception as exc:
        raise AgoraServiceError("failed to generate Agora RTC+RTM token") from exc


def _convo_ai_auth() -> tuple[str, str]:
    settings = get_settings()
    customer_secret = settings.agora_customer_secret.get_secret_value()
    if not settings.agora_customer_id.strip() or not customer_secret:
        raise AgoraServiceError(
            "AGORA_CUSTOMER_ID and AGORA_CUSTOMER_SECRET are required to start the AI agent"
        )
    return settings.agora_customer_id, customer_secret


async def start_agent_session(
    channel_name: str,
    remote_uid: int,
    *,
    student_context: str = "",
    prior_context: str = "",
) -> dict[str, Any]:
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
    system_context = f"""You are Margdarshak, a warm campus placement support chatbot.
Known student profile: {student_context or 'No profile is available.'}
Relevant earlier conversation: {prior_context or 'None.'}

Never ask for facts already present in the known profile. Address the student by first name.
First identify whether they need placement support or a learning resource.

For a learning resource, collect only missing details: exact skill/topic, preferred study style
(hands-on practice, video lessons, or reading), desired pace (short crash course or deep dive),
and budget (free or paid). Ask one specific question at a time and briefly reflect newly learned
facts.

For a placement issue, behave like a support chatbot:
- Listen and let the student describe the problem in their own words.
- Ask only for missing concrete details needed to file the ticket (company or drive name,
  what went wrong, and what they need fixed). Ask at most one short clarifying question if needed.
- Do NOT ask whether the issue is urgent or time-sensitive.
- Do NOT ask about phone calls, dialler buttons, or calling support.
- Once the issue is clear, briefly acknowledge that you are submitting it for routing.
  A separate routing agent will group it with similar open issues or connect the student
  to the placement coordinator. Do not invent coordinator names or promise immediate human reply.
- Keep spoken replies under three sentences.

Avoid generic questions such as 'tell me more'. Do not invent university policies,
deadlines, courses, or student facts. Never read a URL aloud; say that the link has been added to
the live card so the student can open or copy it."""
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
            "llm": {
                "system_messages": [{"role": "system", "content": system_context}],
                "greeting_message": (
                    "Hi! I already have your student profile. Tell me what you need "
                    "help with — a placement issue, or finding a learning resource?"
                ),
            },
            "advanced_features": {"enable_rtm": True},
            "parameters": {
                "data_channel": "rtm",
                "transcript": {"enable": True, "protocol_version": "v2"},
            },
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


async def speak_to_student(
    agent_id: str,
    text: str,
    *,
    priority: str = "INTERRUPT",
    interruptable: bool = True,
) -> dict[str, Any]:
    """Broadcast a routing reply through the live Conversational AI agent TTS."""

    message = text.strip()
    if not agent_id.strip():
        raise AgoraServiceError("agent_id must not be empty")
    if not message:
        raise AgoraServiceError("speak text must not be empty")
    if len(message.encode("utf-8")) > 512:
        message = message.encode("utf-8")[:500].decode("utf-8", errors="ignore").rstrip()

    settings = get_settings()
    url = (
        f"{settings.agora_convo_ai_base_url.rstrip('/')}/"
        f"{settings.agora_app_id}/agents/{agent_id}/speak"
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                url,
                json={
                    "text": message,
                    "priority": priority,
                    "interruptable": interruptable,
                },
                auth=_convo_ai_auth(),
                headers={"Accept": "application/json"},
            )
        if response.status_code not in {200, 204}:
            response.raise_for_status()
        return {
            "agent_id": agent_id,
            "status": "spoken",
            "text": message,
        }
    except AgoraServiceError:
        raise
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise AgoraServiceError(
            f"Agora rejected speak request ({exc.response.status_code}): {detail}"
        ) from exc
    except httpx.HTTPError as exc:
        raise AgoraServiceError("failed to speak through Agora agent") from exc


async def notify_coordinator(
    channel_name: str,
    poc_contact: str,
    summary: str,
    *,
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Notify the placement coordinator after a routing decision via Agora."""

    return await handover_to_human(
        channel_name, poc_contact, summary, agent_id=agent_id
    )


async def handover_to_human(
    channel_name: str,
    poc_contact: str,
    summary: str,
    *,
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Invite a human POC to the live channel with concise case context."""

    if not channel_name.strip():
        raise AgoraServiceError("channel_name must not be empty")
    if not poc_contact.strip():
        raise AgoraServiceError("poc_contact must not be empty")
    if not summary.strip():
        raise AgoraServiceError("case summary must not be empty")

    # Persist a coordinator handoff brief. Student-facing replies are spoken by
    # the query routing agent via speak_to_student after the routing decision.
    return {
        "channel_name": channel_name,
        "poc_contact": poc_contact,
        "status": "handover_pending",
        "summary_delivered": True,
        "summary": summary[:2000],
        "agent_id": agent_id,
    }
