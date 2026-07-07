from telegram import BotCommand
from telegram.ext import Application

from bot.handlers import get_handlers
from core.config import get_settings
from core.redis_client import RedisClient
from services.filtering import FilteringService
from services.scheduler import setup_scheduler

BOT_COMMANDS = [
    BotCommand("start", "Запустить бота и показать помощь"),
    BotCommand("truck", "Настроить параметры фуры"),
    BotCommand("cancel", "Отменить текущую настройку"),
]


def create_application() -> Application:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")

    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(_on_startup)
        .post_shutdown(_on_shutdown)
        .build()
    )

    application.bot_data["redis_client"] = RedisClient()
    application.bot_data["filtering_service"] = FilteringService()

    for handler in get_handlers():
        application.add_handler(handler)

    return application


async def _on_startup(application: Application) -> None:
    from core.config import get_settings
    from core.database import init_db
    from core.logger import logger

    cfg = get_settings()
    logger.info(
        "Env check: database=%s, redis=%s, railway=%s",
        "ok" if cfg.has_database_config else "MISSING",
        "ok" if cfg.has_redis_config else "missing",
        "yes" if cfg.is_railway else "no",
    )
    if not cfg.has_database_config:
        logger.error(
            "DATABASE_URL не задан в сервисе cargobot. "
            "Variables → Add Reference → cargobot-db → DATABASE_URL → Deploy"
        )
    if not cfg.has_redis_config:
        logger.warning(
            "REDIS_URL не задан — дедупликация может не работать. "
            "Добавьте Redis-сервис и reference REDIS_URL"
        )

    await init_db()

    await application.bot.set_my_commands(BOT_COMMANDS)
    logger.info("Bot command menu registered")

    redis: RedisClient = application.bot_data["redis_client"]
    if await redis.ping():
        logger.info("Redis connected")
    else:
        logger.warning("Redis not available")

    scheduler = setup_scheduler(application)
    application.bot_data["scheduler"] = scheduler
    scheduler.start()
    logger.info("CargoBot started")


async def _on_shutdown(application: Application) -> None:
    from core.logger import logger

    scheduler = application.bot_data.get("scheduler")
    if scheduler:
        scheduler.shutdown()

    redis: RedisClient = application.bot_data.get("redis_client")
    if redis:
        await redis.close()

    logger.info("CargoBot stopped")
