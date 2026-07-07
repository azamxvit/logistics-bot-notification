from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.handlers.truck.states import PREVIOUS_STATE


async def send_step(
    update: Update,
    text: str,
    reply_markup,
    parse_mode: str = "Markdown",
) -> None:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    elif update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)


async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE, current_state: int) -> int:
    from bot.handlers.truck import steps

    previous = PREVIOUS_STATE.get(current_state)
    if previous is None:
        if update.callback_query:
            await update.callback_query.answer("Это первый шаг")
        return current_state
    return await steps.show_state(update, context, previous)


async def cancel_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Настройка отменена.")
    elif update.message:
        await update.message.reply_text("❌ Настройка отменена.")
    context.user_data.clear()
    return ConversationHandler.END
