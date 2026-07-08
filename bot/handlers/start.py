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
        "*Доступные команды:*\n"
        "/start — это сообщение\n"
        "/truck — ваши фуры (до 3): добавить, изменить, задать время поиска\n"
        "/cancel — отменить текущую настройку\n\n"
        "Меню команд также доступно по кнопке *«/»* слева от поля ввода.\n\n"
        "Добавьте фуру через /truck и включите поиск на 1–2 дня, чтобы получать заявки."
    )
    await update.message.reply_text(text, parse_mode="Markdown")
    logger.info("User %s started bot", user.id)
