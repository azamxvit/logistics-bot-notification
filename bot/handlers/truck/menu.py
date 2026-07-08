from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.truck import prompts
from bot.handlers.truck.keyboards import (
    menu_keyboard,
    search_window_keyboard,
    truck_detail_keyboard,
)
from bot.handlers.truck.navigation import send_step
from bot.handlers.truck.states import MENU, SEARCH_WINDOW
from core.database import async_session_factory
from models.db_models import MAX_TRUCKS_PER_USER
from repositories.truck_repository import TruckRepository


async def render_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["_truck_state"] = MENU
    user = update.effective_user
    async with async_session_factory() as session:
        repo = TruckRepository(session)
        trucks = await repo.list_by_telegram_id(user.id)

    can_add = len(trucks) < MAX_TRUCKS_PER_USER
    text = prompts.prompt_menu(trucks, MAX_TRUCKS_PER_USER)
    await send_step(update, text, menu_keyboard(trucks, can_add))
    return MENU


async def render_truck_detail(
    update: Update, context: ContextTypes.DEFAULT_TYPE, profile_id: int
) -> int:
    user = update.effective_user
    async with async_session_factory() as session:
        repo = TruckRepository(session)
        truck = await repo.get_by_id(profile_id, user.id)

    if not truck:
        return await render_menu(update, context)

    await send_step(update, prompts.prompt_truck_detail(truck), truck_detail_keyboard(truck.id))
    return MENU


async def render_search_window(
    update: Update, context: ContextTypes.DEFAULT_TYPE, profile_id: int
) -> int:
    context.user_data["_truck_state"] = SEARCH_WINDOW
    user = update.effective_user
    async with async_session_factory() as session:
        repo = TruckRepository(session)
        truck = await repo.get_by_id(profile_id, user.id)

    if not truck:
        return await render_menu(update, context)

    await send_step(update, prompts.prompt_search_window(truck.label), search_window_keyboard(truck.id))
    return SEARCH_WINDOW
