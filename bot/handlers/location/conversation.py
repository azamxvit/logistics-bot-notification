from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.handlers.location.handlers import (
    LOC_CITY,
    LOC_PICK,
    handle_location_cancel,
    handle_location_city,
    handle_location_clear,
    handle_location_pick,
    location_start,
)

PICK_PATTERN = r"^loc:pick:\d+$"
FROM_TRUCK_PATTERN = r"^truck:menu:loc:\d+$"
CLEAR_PATTERN = r"^loc:clear:\d+$"


def build_location_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("location", location_start),
            CallbackQueryHandler(handle_location_pick, pattern=PICK_PATTERN),
        ],
        states={
            LOC_PICK: [
                CallbackQueryHandler(handle_location_pick, pattern=PICK_PATTERN),
                CallbackQueryHandler(handle_location_cancel, pattern=r"^loc:cancel$"),
            ],
            LOC_CITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_location_city),
                CallbackQueryHandler(handle_location_clear, pattern=CLEAR_PATTERN),
                CallbackQueryHandler(handle_location_cancel, pattern=r"^loc:cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handle_location_cancel),
            CallbackQueryHandler(handle_location_cancel, pattern=r"^loc:cancel$"),
        ],
        allow_reentry=True,
    )
