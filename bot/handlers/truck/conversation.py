from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

from bot.handlers.truck import handlers
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

BACK_PATTERN = r"^truck:back$"
CANCEL_PATTERN = r"^truck:cancel$"
BODY_PATTERN = r"^truck:body:"
CERT_TOGGLE_PATTERN = r"^truck:cert:toggle:"
CERT_DONE_PATTERN = r"^truck:cert:done$"
CARGO_TOGGLE_PATTERN = r"^truck:cargo:toggle:"
CARGO_DONE_PATTERN = r"^truck:cargo:done$"


def build_truck_conversation() -> ConversationHandler:
    nav_handlers = [
        CallbackQueryHandler(handlers.handle_back, pattern=BACK_PATTERN),
        CallbackQueryHandler(handlers.handle_cancel, pattern=CANCEL_PATTERN),
    ]

    return ConversationHandler(
        entry_points=[CommandHandler("truck", handlers.truck_start)],
        states={
            TRUCK_COUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_truck_count),
                *nav_handlers,
            ],
            TONNAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_tonnage),
                *nav_handlers,
            ],
            VOLUME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_volume),
                *nav_handlers,
            ],
            BODY_TYPE: [
                CallbackQueryHandler(handlers.handle_body_type_callback, pattern=BODY_PATTERN),
                *nav_handlers,
            ],
            CERTIFICATIONS: [
                CallbackQueryHandler(handlers.handle_cert_toggle, pattern=CERT_TOGGLE_PATTERN),
                CallbackQueryHandler(handlers.handle_cert_done, pattern=CERT_DONE_PATTERN),
                *nav_handlers,
            ],
            CARGO_TYPES: [
                CallbackQueryHandler(handlers.handle_cargo_toggle, pattern=CARGO_TOGGLE_PATTERN),
                CallbackQueryHandler(handlers.handle_cargo_done, pattern=CARGO_DONE_PATTERN),
                *nav_handlers,
            ],
            MIN_RATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_min_rate),
                *nav_handlers,
            ],
            ORIGINS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_origins),
                *nav_handlers,
            ],
            DESTINATIONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_destinations),
                *nav_handlers,
            ],
            CONFIRM: [
                CallbackQueryHandler(handlers.handle_confirm_save, pattern=r"^truck:confirm:save$"),
                CallbackQueryHandler(handlers.handle_confirm_edit, pattern=r"^truck:confirm:edit$"),
                *nav_handlers,
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handlers.handle_cancel),
            CallbackQueryHandler(handlers.handle_cancel, pattern=r"^truck:cancel$"),
        ],
        allow_reentry=True,
    )
