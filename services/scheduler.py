import random

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from core.config import get_settings
from core.database import async_session_factory
from core.logger import logger
from repositories.truck_repository import TruckRepository
from services.orchestrator import SourceOrchestrator, build_orchestrator


class SchedulerService:
    def __init__(self, orchestrator: SourceOrchestrator, application: Application) -> None:
        self._orchestrator = orchestrator
        self._application = application
        self._scheduler = AsyncIOScheduler()
        self._settings = get_settings()

    def start(self) -> None:
        interval = random.randint(
            self._settings.scheduler_interval_min,
            self._settings.scheduler_interval_max,
        )
        self._scheduler.add_job(
            self._run_job,
            "interval",
            minutes=interval,
            id="source_poll",
            replace_existing=True,
            max_instances=1,
        )
        self._scheduler.add_job(
            self._check_expired,
            "interval",
            minutes=5,
            id="expire_check",
            replace_existing=True,
            max_instances=1,
        )
        self._scheduler.start()
        logger.info("Scheduler started, polling every %d minutes", interval)

    async def _run_job(self) -> None:
        logger.info("Starting scheduled source poll")
        try:
            count = await self._orchestrator.run_cycle()
            logger.info("Poll complete, %d new requests", count)
        except Exception as exc:
            logger.error("Scheduled poll failed: %s", exc, exc_info=True)

    async def _check_expired(self) -> None:
        try:
            async with async_session_factory() as session:
                repo = TruckRepository(session)
                expired = await repo.get_expired_profiles()
                for profile in expired:
                    telegram_id = profile.user.telegram_user_id if profile.user else None
                    label = profile.label
                    await repo.deactivate(profile.id)
                    if telegram_id:
                        try:
                            await self._application.bot.send_message(
                                chat_id=telegram_id,
                                text=(
                                    f"⏳ Поиск по «{label}» завершён.\n"
                                    "Чтобы запустить снова, откройте /truck → выберите фуру → «Время поиска»."
                                ),
                            )
                        except Exception as exc:
                            logger.error("Failed to notify expiry for user %s: %s", telegram_id, exc)
        except Exception as exc:
            logger.error("Expiry check failed: %s", exc, exc_info=True)

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)


def setup_scheduler(application: Application) -> SchedulerService:
    orchestrator = build_orchestrator(application)
    application.bot_data["orchestrator"] = orchestrator
    return SchedulerService(orchestrator, application)
