import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.db.redis import get_redis_client
from app.db.session_factory import get_session_factory
from app.models.chat_bridge import BridgeStatus, ChatBridge
from app.services.matchmaker_service import MESSAGE_KEY

logger = logging.getLogger(__name__)


async def expire_due_bridges() -> int:
    """Expire due bridges in Postgres and remove their ephemeral messages."""

    async with get_session_factory()() as db:
        async with db.begin():
            bridges = (
                await db.scalars(
                    select(ChatBridge)
                    .where(
                        ChatBridge.status == BridgeStatus.ACTIVE,
                        ChatBridge.expires_at < datetime.now(timezone.utc),
                    )
                    .with_for_update(skip_locked=True)
                )
            ).all()
            bridge_ids = [bridge.id for bridge in bridges]
            for bridge in bridges:
                bridge.status = BridgeStatus.EXPIRED

    if bridge_ids:
        keys = [MESSAGE_KEY.format(bridge_id=bridge_id) for bridge_id in bridge_ids]
        try:
            await get_redis_client().delete(*keys)
        except Exception:
            logger.exception("failed_to_delete_expired_bridge_messages")

    if bridge_ids:
        logger.info("expired_matchmaker_bridges", extra={"count": len(bridge_ids)})
    return len(bridge_ids)


async def expiry_worker_loop(stop_event: asyncio.Event) -> None:
    interval = get_settings().expiry_worker_interval_seconds
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            try:
                await expire_due_bridges()
            except Exception:
                logger.exception("matchmaker_expiry_worker_failed")
