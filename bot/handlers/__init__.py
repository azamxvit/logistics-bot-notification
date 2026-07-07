from telegram.ext import CommandHandler

from bot.handlers.start import start_handler
from bot.handlers.truck.conversation import build_truck_conversation


def get_handlers() -> list:
    return [
        CommandHandler("start", start_handler),
        build_truck_conversation(),
    ]
