from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.truck import prompts
from bot.handlers.truck.keyboards import (
    body_type_keyboard,
    cargo_types_keyboard,
    certifications_keyboard,
    confirm_keyboard,
    text_step_keyboard,
)
from bot.handlers.truck.states import (
    BODY_TYPE,
    CARGO_TYPES,
    CERTIFICATIONS,
    CONFIRM,
    DESTINATIONS,
    MIN_RATE,
    ORIGINS,
    TONNAGE,
    TRUCK_COUNT,
    VOLUME,
)
from bot.handlers.truck.navigation import send_step


async def show_state(update: Update, context: ContextTypes.DEFAULT_TYPE, state: int) -> int:
    context.user_data["_truck_state"] = state
    data = context.user_data

    if state == TRUCK_COUNT:
        await send_step(update, prompts.prompt_truck_count(data.get("truck_count")), text_step_keyboard())
    elif state == TONNAGE:
        await send_step(update, prompts.prompt_tonnage(data.get("tonnage")), text_step_keyboard())
    elif state == VOLUME:
        await send_step(update, prompts.prompt_volume(data.get("volume")), text_step_keyboard())
    elif state == BODY_TYPE:
        await send_step(update, prompts.prompt_body_type(data.get("body_type")), body_type_keyboard())
    elif state == CERTIFICATIONS:
        selected = set(data.get("certifications", []))
        await send_step(update, prompts.prompt_certifications(selected), certifications_keyboard(selected))
    elif state == CARGO_TYPES:
        selected = set(data.get("accepted_cargo_types", []))
        await send_step(update, prompts.prompt_cargo_types(selected), cargo_types_keyboard(selected))
    elif state == MIN_RATE:
        await send_step(update, prompts.prompt_min_rate(data.get("min_rate")), text_step_keyboard())
    elif state == ORIGINS:
        await send_step(update, prompts.prompt_origins(data.get("origins")), text_step_keyboard())
    elif state == DESTINATIONS:
        await send_step(update, prompts.prompt_destinations(data.get("destinations")), text_step_keyboard())
    elif state == CONFIRM:
        await send_step(update, prompts.build_summary(data), confirm_keyboard())

    return state
