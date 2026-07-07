from collections.abc import Callable, Awaitable

from telegram.ext import Application

from core.database import async_session_factory
from core.logger import logger
from core.redis_client import RedisClient
from models.db_models import CargoRequest
from repositories.request_repository import RequestRepository
from repositories.truck_repository import UserRepository
from services.filtering import FilteringService
from sources.ati_su import DISPLAY_NAME as ATI_DISPLAY
from sources.base import BaseSource
from sources.deliver_kz import DISPLAY_NAME as DELIVER_DISPLAY
from sources.factory import build_sources

SOURCE_DISPLAY_NAMES = {
    "ati_su": ATI_DISPLAY,
    "deliver_kz": DELIVER_DISPLAY,
}

NotifyCallback = Callable[[int, CargoRequest], Awaitable[None]]


class SourceOrchestrator:
    def __init__(
        self,
        redis_client: RedisClient,
        filtering_service: FilteringService,
        sources: list[BaseSource] | None = None,
        on_match: NotifyCallback | None = None,
    ) -> None:
        self._redis = redis_client
        self._filtering = filtering_service
        self._sources = sources or build_sources()
        self._on_match = on_match

    async def run_cycle(self) -> int:
        new_count = 0
        for source in self._sources:
            try:
                new_count += await self._process_source(source)
            except Exception as exc:
                logger.error("Source %s failed entirely: %s", source.name, exc, exc_info=True)
        return new_count

    async def _process_source(self, source: BaseSource) -> int:
        parsed = await source.run()
        if not parsed:
            logger.warning(
                "[%s] 0 заявок — проверьте cookie/API или включите ENABLE_DEMO_SOURCE=true",
                source.name,
            )
        new_count = 0

        async with async_session_factory() as session:
            request_repo = RequestRepository(session)
            user_repo = UserRepository(session)

            for item in parsed:
                content_hash = RedisClient.compute_hash(item.dedup_payload())

                if await self._redis.is_duplicate(content_hash):
                    continue

                existing = await request_repo.get_by_hash(content_hash)
                if existing:
                    await self._redis.mark_seen(content_hash)
                    continue

                saved = await request_repo.create(item, content_hash)
                await self._redis.mark_seen(content_hash)
                new_count += 1

                await self._notify_matching_users(user_repo, saved)

        return new_count

    async def _notify_matching_users(self, user_repo: UserRepository, request: CargoRequest) -> None:
        if not self._on_match:
            return

        users = await user_repo.get_all_with_trucks()
        for user in users:
            if user.truck_profile and self._filtering.matches(request, user.truck_profile):
                try:
                    await self._on_match(user.telegram_user_id, request)
                except Exception as exc:
                    logger.error(
                        "Failed to notify user %s: %s",
                        user.telegram_user_id,
                        exc,
                        exc_info=True,
                    )


def build_orchestrator(application: Application) -> SourceOrchestrator:
    redis_client: RedisClient = application.bot_data["redis_client"]
    filtering_service: FilteringService = application.bot_data["filtering_service"]

    async def notify(user_id: int, request: CargoRequest) -> None:
        from bot.formatters.request_formatter import RequestFormatter

        text = RequestFormatter.format(request, SOURCE_DISPLAY_NAMES.get(request.source, request.source))
        await application.bot.send_message(chat_id=user_id, text=text, disable_web_page_preview=True)

    return SourceOrchestrator(
        redis_client=redis_client,
        filtering_service=filtering_service,
        on_match=notify,
    )
