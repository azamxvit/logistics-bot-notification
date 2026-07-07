"""Разовый запуск парсеров (аналог cron-скрипта). Использование: python scripts/scrape_once.py"""

import asyncio

from core.database import async_session_factory, init_db
from core.logger import logger, setup_logging
from core.redis_client import RedisClient
from services.orchestrator import SourceOrchestrator
from services.filtering import FilteringService
from sources.factory import build_sources


async def main() -> None:
    setup_logging()
    await init_db()
    redis = RedisClient()
    orchestrator = SourceOrchestrator(
        redis_client=redis,
        filtering_service=FilteringService(),
        sources=build_sources(),
    )
    count = await orchestrator.run_cycle()
    logger.info("Scrape finished, new requests: %d", count)
    await redis.close()


if __name__ == "__main__":
    asyncio.run(main())
