import sys
import time

from core.config import get_settings
from core.logger import logger


def main() -> None:
    logger.info("Starting CargoBot...")

    settings = get_settings()
    if not settings.has_database_config:
        logger.error(
            "DATABASE_URL не передан в контейнер.\n"
            "Railway → сервис cargobot → Variables → New Variable → Add Reference → "
            "cargobot-db → DATABASE_URL, затем нажать Deploy (Apply changes)."
        )
        # Пауза, чтобы Railway не крутил рестарты слишком часто
        time.sleep(30)
        sys.exit(1)

    from bot.bot import create_application

    application = create_application()
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
