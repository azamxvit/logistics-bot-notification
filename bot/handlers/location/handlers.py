from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from core.database import async_session_factory
from core.logger import logger
from repositories.truck_repository import TruckRepository, UserRepository

LOC_PICK, LOC_CITY = range(2)


def _pick_keyboard(trucks: list) -> InlineKeyboardMarkup:
    rows = []
    for truck in trucks:
        loc = f" — {truck.current_city}" if truck.current_city else ""
        rows.append(
            [
                InlineKeyboardButton(
                    f"🚛 {truck.label}{loc}",
                    callback_data=f"loc:pick:{truck.id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton("❌ Отмена", callback_data="loc:cancel")])
    return InlineKeyboardMarkup(rows)


def _city_keyboard(profile_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🗑 Сбросить город", callback_data=f"loc:clear:{profile_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="loc:cancel")],
        ]
    )


async def location_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.effective_user:
        return ConversationHandler.END

    user = update.effective_user
    async with async_session_factory() as session:
        await UserRepository(session).get_or_create(
            telegram_user_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )
        trucks = await TruckRepository(session).list_by_telegram_id(user.id)

    if not trucks:
        await update.message.reply_text(
            "Сначала добавьте фуру через /truck, затем укажите город где она стоит."
        )
        return ConversationHandler.END

    if len(trucks) == 1:
        context.user_data["location_truck_id"] = trucks[0].id
        context.user_data["location_truck_label"] = trucks[0].label
        current = trucks[0].current_city or "не задан"
        await update.message.reply_text(
            f"📍 *{trucks[0].label}*\n"
            f"Сейчас: *{current}*\n\n"
            "Введите город, где стоит фура.\n"
            "_Пример: Атырау, Алматы, Махамбет_\n\n"
            "Буду присылать заявки только с погрузкой из этого города.\n"
            "Атырау ≠ Индер — это разные города.",
            parse_mode="Markdown",
            reply_markup=_city_keyboard(trucks[0].id),
        )
        return LOC_CITY

    text = (
        "📍 *Где стоит фура?*\n\n"
        "Выберите фуру, затем введите город.\n"
        "Заявки будут только с погрузкой из этого города (без км и адресов)."
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=_pick_keyboard(trucks))
    return LOC_PICK


async def handle_location_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.data or not user:
        return LOC_PICK

    profile_id = int(query.data.rsplit(":", 1)[-1])
    async with async_session_factory() as session:
        truck = await TruckRepository(session).get_by_id(profile_id, user.id)

    if not truck:
        await query.answer("Фура не найдена")
        return LOC_PICK

    context.user_data["location_truck_id"] = truck.id
    context.user_data["location_truck_label"] = truck.label
    current = truck.current_city or "не задан"
    await query.answer()
    await query.edit_message_text(
        f"📍 *{truck.label}*\n"
        f"Сейчас: *{current}*\n\n"
        "Введите город, где стоит фура.\n"
        "_Пример: Атырау, Алматы, Махамбет_",
        parse_mode="Markdown",
        reply_markup=_city_keyboard(truck.id),
    )
    return LOC_CITY


async def handle_location_from_truck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Вход из меню фуры: truck:menu:loc:{id}"""
    return await handle_location_pick(update, context)


async def handle_location_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.effective_user:
        return LOC_CITY

    city = (update.message.text or "").strip()
    if len(city) < 2:
        await update.message.reply_text("❌ Введите название города, например: Атырау")
        return LOC_CITY

    profile_id = context.user_data.get("location_truck_id")
    label = context.user_data.get("location_truck_label", "Фура")
    if not profile_id:
        return ConversationHandler.END

    async with async_session_factory() as session:
        truck = await TruckRepository(session).set_current_city(
            profile_id, update.effective_user.id, city
        )

    if not truck:
        await update.message.reply_text("❌ Фура не найдена.")
        return ConversationHandler.END

    await update.message.reply_text(
        f"✅ *{label}* — город: *{city}*\n\n"
        "Буду присылать заявки с погрузкой только из этого города.\n"
        "Чтобы сменить — снова /location",
        parse_mode="Markdown",
    )
    logger.info("User %s set location %s for truck %s", update.effective_user.id, city, profile_id)
    context.user_data.clear()
    return ConversationHandler.END


async def handle_location_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.data or not user:
        return LOC_CITY

    profile_id = int(query.data.rsplit(":", 1)[-1])
    async with async_session_factory() as session:
        truck = await TruckRepository(session).clear_current_city(profile_id, user.id)

    if not truck:
        await query.answer("Не найдено")
        return LOC_CITY

    await query.answer("Город сброшен")
    await query.edit_message_text(
        f"📍 *{truck.label}*\n\n"
        "Город сброшен — геофильтр выключен.\n"
        "Заявки снова по настройкам «Откуда» в профиле фуры.",
        parse_mode="Markdown",
    )
    context.user_data.clear()
    return ConversationHandler.END


async def handle_location_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Отменено.")
    elif update.message:
        await update.message.reply_text("❌ Отменено.")
    context.user_data.clear()
    return ConversationHandler.END
