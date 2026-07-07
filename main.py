from bot.bot import create_application
from core.logger import logger


def main() -> None:
    logger.info("Starting CargoBot...")
    application = create_application()
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
