from telegram.ext import CommandHandler

from bot.handlers.location.conversation import build_location_conversation
from bot.handlers.start import start_handler
from bot.handlers.truck.conversation import build_truck_conversation


def get_handlers() -> list:
    return [
        CommandHandler("start", start_handler),
        build_truck_conversation(),
        build_location_conversation(),
    ]
