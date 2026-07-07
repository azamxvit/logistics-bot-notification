from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.handlers.truck import steps
from bot.handlers.truck.keyboards import cargo_types_keyboard, certifications_keyboard
from bot.handlers.truck.navigation import cancel_dialog, go_back, send_step
from bot.handlers.truck.prompts import build_summary, prompt_certifications, prompt_cargo_types
from bot.handlers.truck.states import (
    BODY_TYPE,
    CARGO_TYPES,
    CERTIFICATIONS,
    CONFIRM,
    DESTINATIONS,
    MIN_RATE,
    ORIGINS,
    SKIP_TEXTS,
    TONNAGE,
    TRUCK_COUNT,
    VOLUME,
)
from core.database import async_session_factory
from core.logger import logger
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


def _parse_positive_int(text: str) -> int | None:
    try:
        value = int(text.strip())
        if value <= 0:
            return None
        return value
    except (ValueError, AttributeError):
        return None


async def truck_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.effective_user:
        return ConversationHandler.END
    context.user_data.clear()
    context.user_data["certifications"] = []
    context.user_data["accepted_cargo_types"] = {"general"}
    return await steps.show_state(update, context, TRUCK_COUNT)


async def handle_truck_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return TRUCK_COUNT
    count = _parse_positive_int(update.message.text or "")
    if count is None:
        await update.message.reply_text(
            "❌ Нужно целое число больше 0.\n_Пример: 1_",
            parse_mode="Markdown",
        )
        return TRUCK_COUNT
    context.user_data["truck_count"] = count
    return await steps.show_state(update, context, TONNAGE)


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
        truck_count=data.get("truck_count", 1),
        tonnage_tons=data["tonnage"],
        volume_m3=data["volume"],
        body_type=data.get("body_type", "any"),
        certifications=list(data.get("certifications", [])),
        accepted_cargo_types=sorted(data.get("accepted_cargo_types", {"general"})),
        min_rate=data.get("min_rate"),
        origin_cities=data.get("origins"),
        destination_cities=data.get("destinations"),
    )

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        truck_repo = TruckRepository(session)
        await user_repo.get_or_create(
            telegram_user_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )
        await truck_repo.upsert(user.id, profile_data)

    summary = build_summary(data)
    final_text = (
        f"✅ *Профиль фуры сохранён!*\n\n"
        f"{summary.split('Сохранить профиль?')[0].strip()}\n\n"
        "Теперь вы будете получать подходящие заявки."
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(final_text, parse_mode="Markdown")
    logger.info("Truck profile saved for user %s", user.id)
    context.user_data.clear()
    return ConversationHandler.END


async def handle_confirm_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await steps.show_state(update, context, TRUCK_COUNT)


async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    current = context.user_data.get("_truck_state", TRUCK_COUNT)
    return await go_back(update, context, current)


async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await cancel_dialog(update, context)
