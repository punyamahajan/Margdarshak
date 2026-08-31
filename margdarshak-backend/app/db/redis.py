from functools import lru_cache
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings

if TYPE_CHECKING:
    from redis.asyncio import Redis


@lru_cache
def get_redis_client() -> "Redis | Any":
    from redis.asyncio import Redis

    return Redis.from_url(
        get_settings().redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
