from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.handlers.truck import menu, steps
from bot.handlers.truck.keyboards import cargo_types_keyboard, certifications_keyboard
from bot.handlers.truck.navigation import cancel_dialog, go_back, send_step
from bot.handlers.truck.prompts import prompt_certifications, prompt_cargo_types
from bot.handlers.truck.states import (
    BODY_TYPE,
    CARGO_TYPES,
    CERTIFICATIONS,
    CONFIRM,
    DESTINATIONS,
    LOCATION_CITY,
    MENU,
    MIN_RATE,
    ORIGINS,
    SEARCH_WINDOW,
    SKIP_TEXTS,
    TONNAGE,
    VOLUME,
)
from core.database import async_session_factory
from core.logger import logger
from models.db_models import MAX_TRUCKS_PER_USER
from models.schemas import TruckProfileData
from repositories.truck_repository import TruckRepository, UserRepository


def _parse_positive_float(text: str) -> float | None:
    try:
        value = float(text.replace(",", ".").strip())
        if value <= 0:
            return None
        return value
    except (ValueError, AttributeError):
        return None


def _reset_wizard(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in (
        "editing_truck_id",
        "label",
        "tonnage",
        "volume",
        "body_type",
        "min_rate",
        "origins",
        "destinations",
    ):
        context.user_data.pop(key, None)
    context.user_data["certifications"] = []
    context.user_data["accepted_cargo_types"] = {"general"}


# --- Вход и меню ---


async def truck_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.effective_user:
        return ConversationHandler.END
    user = update.effective_user
    async with async_session_factory() as session:
        await UserRepository(session).get_or_create(
            telegram_user_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )
    context.user_data.clear()
    return await menu.render_menu(update, context)


async def handle_menu_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    async with async_session_factory() as session:
        count = await TruckRepository(session).count_by_telegram_id(user.id)

    if count >= MAX_TRUCKS_PER_USER:
        if update.callback_query:
            await update.callback_query.answer(
                f"Достигнут лимит {MAX_TRUCKS_PER_USER} фур. Удалите одну, чтобы добавить новую.",
                show_alert=True,
            )
        return MENU

    _reset_wizard(context)
    context.user_data["editing_truck_id"] = None
    context.user_data["label"] = f"Фура {count + 1}"
    return await steps.show_state(update, context, TONNAGE)


async def handle_menu_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    profile_id = _extract_id(update)
    if profile_id is None:
        return MENU
    return await menu.render_truck_detail(update, context, profile_id)


async def handle_menu_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await menu.render_menu(update, context)


async def handle_menu_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    profile_id = _extract_id(update)
    user = update.effective_user
    if profile_id is None:
        return MENU

    async with async_session_factory() as session:
        truck = await TruckRepository(session).get_by_id(profile_id, user.id)

    if not truck:
        return await menu.render_menu(update, context)

    _reset_wizard(context)
    context.user_data["editing_truck_id"] = truck.id
    context.user_data["label"] = truck.label
    context.user_data["tonnage"] = truck.tonnage_tons
    context.user_data["volume"] = truck.volume_m3
    context.user_data["body_type"] = truck.body_type
    context.user_data["certifications"] = list(truck.certifications or [])
    context.user_data["accepted_cargo_types"] = set(truck.accepted_cargo_types or ["general"])
    context.user_data["min_rate"] = truck.min_rate
    context.user_data["origins"] = truck.origin_cities
    context.user_data["destinations"] = truck.destination_cities
    return await steps.show_state(update, context, TONNAGE)


async def handle_menu_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    profile_id = _extract_id(update)
    user = update.effective_user
    if profile_id is None:
        return MENU
    async with async_session_factory() as session:
        deleted = await TruckRepository(session).delete(profile_id, user.id)
    if update.callback_query:
        await update.callback_query.answer("Удалено" if deleted else "Не найдено")
    return await menu.render_menu(update, context)


async def handle_menu_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    profile_id = _extract_id(update)
    if profile_id is None:
        return MENU
    return await menu.render_search_window(update, context, profile_id)


async def handle_menu_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from bot.handlers.location.handlers import _city_keyboard

    query = update.callback_query
    user = update.effective_user
    profile_id = _extract_id(update)
    if not query or not user or profile_id is None:
        return MENU

    async with async_session_factory() as session:
        truck = await TruckRepository(session).get_by_id(profile_id, user.id)

    if not truck:
        await query.answer("Фура не найдена")
        return MENU

    context.user_data["location_truck_id"] = truck.id
    context.user_data["location_truck_label"] = truck.label
    context.user_data["location_return_menu"] = True
    current = truck.current_city or "не задан"
    await query.answer()
    await query.edit_message_text(
        f"📍 *{truck.label}*\n"
        f"Сейчас: *{current}*\n\n"
        "Введите город, где стоит фура.\n"
        "_Пример: Атырау, Алматы, Махамбет_\n\n"
        "Заявки только с погрузкой из этого города.",
        parse_mode="Markdown",
        reply_markup=_city_keyboard(truck.id),
    )
    return LOCATION_CITY


async def handle_truck_location_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.effective_user:
        return LOCATION_CITY

    city = (update.message.text or "").strip()
    if len(city) < 2:
        await update.message.reply_text("❌ Введите название города, например: Атырау")
        return LOCATION_CITY

    profile_id = context.user_data.get("location_truck_id")
    label = context.user_data.get("location_truck_label", "Фура")
    if not profile_id:
        return await menu.render_menu(update, context)

    async with async_session_factory() as session:
        truck = await TruckRepository(session).set_current_city(
            profile_id, update.effective_user.id, city
        )

    if not truck:
        await update.message.reply_text("❌ Фура не найдена.")
        return MENU

    context.user_data.pop("location_return_menu", None)
    context.user_data.pop("location_truck_id", None)
    context.user_data.pop("location_truck_label", None)
    logger.info("User %s set location %s for truck %s", update.effective_user.id, city, profile_id)
    await update.message.reply_text(
        f"✅ *{label}* — город: *{city}*\n\n"
        "Заявки с погрузкой только из этого города.",
        parse_mode="Markdown",
    )
    return await menu.render_menu(update, context)


async def handle_truck_location_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.data or not user:
        return LOCATION_CITY

    profile_id = int(query.data.rsplit(":", 1)[-1])
    async with async_session_factory() as session:
        await TruckRepository(session).clear_current_city(profile_id, user.id)

    await query.answer("Город сброшен")
    return await menu.render_menu(update, context)


async def handle_menu_close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("👌 Меню закрыто. Открыть снова — /truck")
    context.user_data.clear()
    return ConversationHandler.END


# --- Мастер настройки ---


async def handle_tonnage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return TONNAGE
    tonnage = _parse_positive_float(update.message.text or "")
    if tonnage is None:
        await update.message.reply_text(
            "❌ Введите число тонн больше 0.\n_Пример: 20_",
            parse_mode="Markdown",
        )
        return TONNAGE
    context.user_data["tonnage"] = tonnage
    return await steps.show_state(update, context, VOLUME)


async def handle_volume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return VOLUME
    volume = _parse_positive_float(update.message.text or "")
    if volume is None:
        await update.message.reply_text(
            "❌ Введите объём в м³ больше 0.\n_Пример: 82_",
            parse_mode="Markdown",
        )
        return VOLUME
    context.user_data["volume"] = volume
    return await steps.show_state(update, context, BODY_TYPE)


async def handle_body_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query or not query.data:
        return BODY_TYPE
    body_type = query.data.removeprefix("truck:body:")
    allowed = {"tent", "refrigerator", "open", "container", "any"}
    if body_type not in allowed:
        await query.answer("Неверный выбор")
        return BODY_TYPE
    context.user_data["body_type"] = body_type
    return await steps.show_state(update, context, CERTIFICATIONS)


async def handle_cert_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query or not query.data:
        return CERTIFICATIONS
    cert = query.data.removeprefix("truck:cert:toggle:")
    selected = set(context.user_data.get("certifications", []))
    if cert in selected:
        selected.discard(cert)
    else:
        selected.add(cert)
    context.user_data["certifications"] = sorted(selected)
    await query.answer()
    await send_step(update, prompt_certifications(selected), certifications_keyboard(selected))
    return CERTIFICATIONS


async def handle_cert_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await steps.show_state(update, context, CARGO_TYPES)


async def handle_cargo_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query or not query.data:
        return CARGO_TYPES
    cargo = query.data.removeprefix("truck:cargo:toggle:")
    selected = set(context.user_data.get("accepted_cargo_types", []))
    if cargo in selected:
        selected.discard(cargo)
    else:
        selected.add(cargo)
    context.user_data["accepted_cargo_types"] = selected
    await query.answer()
    await send_step(update, prompt_cargo_types(selected), cargo_types_keyboard(selected))
    return CARGO_TYPES


async def handle_cargo_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    selected = context.user_data.get("accepted_cargo_types", set())
    if not selected:
        if update.callback_query:
            await update.callback_query.answer("Выберите хотя бы один тип груза", show_alert=True)
        return CARGO_TYPES
    return await steps.show_state(update, context, MIN_RATE)


async def handle_min_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return MIN_RATE
    text = (update.message.text or "").strip()
    if text.lower() in SKIP_TEXTS:
        context.user_data["min_rate"] = None
    else:
        rate = _parse_positive_float(text.replace(" ", ""))
        if rate is None:
            await update.message.reply_text(
                "❌ Введите число больше 0 или «-» для пропуска.\n_Пример: 300000_",
                parse_mode="Markdown",
            )
            return MIN_RATE
        context.user_data["min_rate"] = rate
    return await steps.show_state(update, context, ORIGINS)


async def handle_origins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ORIGINS
    text = (update.message.text or "").strip()
    context.user_data["origins"] = None if text.lower() in SKIP_TEXTS else text
    return await steps.show_state(update, context, DESTINATIONS)


async def handle_destinations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return DESTINATIONS
    text = (update.message.text or "").strip()
    context.user_data["destinations"] = None if text.lower() in SKIP_TEXTS else text
    return await steps.show_state(update, context, CONFIRM)


async def handle_confirm_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    data = context.user_data
    profile_data = TruckProfileData(
        label=data.get("label", "Фура"),
        tonnage_tons=data["tonnage"],
        volume_m3=data["volume"],
        body_type=data.get("body_type", "any"),
        certifications=list(data.get("certifications", [])),
        accepted_cargo_types=sorted(data.get("accepted_cargo_types", {"general"})),
        min_rate=data.get("min_rate"),
        origin_cities=data.get("origins"),
        destination_cities=data.get("destinations"),
    )

    editing_id = data.get("editing_truck_id")
    async with async_session_factory() as session:
        truck_repo = TruckRepository(session)
        try:
            if editing_id:
                saved = await truck_repo.update(editing_id, user.id, profile_data)
            else:
                saved = await truck_repo.create(user.id, profile_data)
        except ValueError as exc:
            if str(exc) == "truck_limit_reached" and update.callback_query:
                await update.callback_query.answer(
                    f"Достигнут лимит {MAX_TRUCKS_PER_USER} фур.", show_alert=True
                )
                return await menu.render_menu(update, context)
            raise

    if not saved:
        return await menu.render_menu(update, context)

    logger.info("Truck profile %s saved for user %s", saved.id, user.id)
    context.user_data["time_truck_id"] = saved.id
    return await menu.render_search_window(update, context, saved.id)


async def handle_confirm_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await steps.show_state(update, context, TONNAGE)


# --- Время поиска ---


async def handle_search_window_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user = update.effective_user
    if not query or not query.data:
        return SEARCH_WINDOW

    # формат: truck:time:set:{id}:{days}
    parts = query.data.split(":")
    try:
        profile_id = int(parts[3])
        days = int(parts[4])
    except (IndexError, ValueError):
        await query.answer("Ошибка")
        return SEARCH_WINDOW

    days = max(1, min(days, 2))
    async with async_session_factory() as session:
        truck = await TruckRepository(session).set_search_window(profile_id, user.id, days)

    if not truck:
        return await menu.render_menu(update, context)

    await query.answer(f"Поиск включён на {days} дн.")
    return await menu.render_menu(update, context)


# --- Навигация ---


async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    current = context.user_data.get("_truck_state", MENU)
    return await go_back(update, context, current)


async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await cancel_dialog(update, context)


def _extract_id(update: Update) -> int | None:
    query = update.callback_query
    if not query or not query.data:
        return None
    try:
        return int(query.data.rsplit(":", 1)[-1])
    except ValueError:
        return None
