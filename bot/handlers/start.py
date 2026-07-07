from telegram import Update
from telegram.ext import ContextTypes

from core.database import async_session_factory
from core.logger import logger
from repositories.truck_repository import UserRepository


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    user = update.effective_user
    async with async_session_factory() as session:
        repo = UserRepository(session)
        await repo.get_or_create(
            telegram_user_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )

    text = (
        "👋 Добро пожаловать в *CargoBot*!\n\n"
        "Я мониторю биржи грузов и присылаю заявки, подходящие под параметры вашей фуры.\n\n"
        "Команды:\n"
        "/start — это сообщение\n"
        "/truck — задать параметры фуры\n\n"
        "Сначала настройте фуру командой /truck, чтобы получать уведомления."
    )
    await update.message.reply_text(text, parse_mode="Markdown")
    logger.info("User %s started bot", user.id)
