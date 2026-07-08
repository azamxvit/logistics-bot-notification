from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

from bot.handlers.truck import handlers
from bot.handlers.truck.states import (
    BODY_TYPE,
    CARGO_TYPES,
    CERTIFICATIONS,
    CONFIRM,
    DESTINATIONS,
    MENU,
    MIN_RATE,
    ORIGINS,
    SEARCH_WINDOW,
    TONNAGE,
    VOLUME,
)

BACK_PATTERN = r"^truck:back$"
CANCEL_PATTERN = r"^truck:cancel$"
BODY_PATTERN = r"^truck:body:"
CERT_TOGGLE_PATTERN = r"^truck:cert:toggle:"
CERT_DONE_PATTERN = r"^truck:cert:done$"
CARGO_TOGGLE_PATTERN = r"^truck:cargo:toggle:"
CARGO_DONE_PATTERN = r"^truck:cargo:done$"


def _menu_handlers() -> list:
    return [
        CallbackQueryHandler(handlers.handle_menu_add, pattern=r"^truck:menu:add$"),
        CallbackQueryHandler(handlers.handle_menu_view, pattern=r"^truck:menu:view:\d+$"),
        CallbackQueryHandler(handlers.handle_menu_edit, pattern=r"^truck:menu:edit:\d+$"),
        CallbackQueryHandler(handlers.handle_menu_delete, pattern=r"^truck:menu:del:\d+$"),
        CallbackQueryHandler(handlers.handle_menu_time, pattern=r"^truck:menu:time:\d+$"),
        CallbackQueryHandler(handlers.handle_menu_list, pattern=r"^truck:menu:list$"),
        CallbackQueryHandler(handlers.handle_menu_close, pattern=r"^truck:menu:close$"),
    ]


def build_truck_conversation() -> ConversationHandler:
    nav_handlers = [
        CallbackQueryHandler(handlers.handle_back, pattern=BACK_PATTERN),
        CallbackQueryHandler(handlers.handle_cancel, pattern=CANCEL_PATTERN),
    ]

    return ConversationHandler(
        entry_points=[CommandHandler("truck", handlers.truck_start)],
        states={
            MENU: _menu_handlers(),
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
            SEARCH_WINDOW: [
                CallbackQueryHandler(
                    handlers.handle_search_window_set, pattern=r"^truck:time:set:\d+:\d+$"
                ),
                CallbackQueryHandler(handlers.handle_menu_list, pattern=r"^truck:menu:list$"),
                *nav_handlers,
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handlers.handle_cancel),
            CallbackQueryHandler(handlers.handle_cancel, pattern=CANCEL_PATTERN),
        ],
        allow_reentry=True,
    )
