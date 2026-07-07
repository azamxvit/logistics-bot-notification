import hashlib
import json
from typing import Any

import redis.asyncio as aioredis

from core.config import get_settings
from core.logger import logger

DEDUP_KEY_PREFIX = "cargobot:dedup:"
DEDUP_TTL_SECONDS = 7 * 24 * 3600


class RedisClient:
    def __init__(self, redis_url: str | None = None) -> None:
        settings = get_settings()
        self._redis = aioredis.from_url(
            redis_url or settings.redis_url,
            decode_responses=True,
        )

    async def close(self) -> None:
        await self._redis.aclose()

    @staticmethod
    def compute_hash(payload: dict[str, Any]) -> str:
        normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def is_duplicate(self, content_hash: str) -> bool:
        key = f"{DEDUP_KEY_PREFIX}{content_hash}"
        return bool(await self._redis.exists(key))

    async def mark_seen(self, content_hash: str) -> None:
        key = f"{DEDUP_KEY_PREFIX}{content_hash}"
        await self._redis.setex(key, DEDUP_TTL_SECONDS, "1")

    async def ping(self) -> bool:
        try:
            return await self._redis.ping()
        except Exception as exc:
            logger.error("Redis ping failed: %s", exc)
            return False
