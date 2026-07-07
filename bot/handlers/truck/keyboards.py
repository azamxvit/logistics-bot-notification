from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.handlers.truck.states import (
    BODY_TYPE_LABELS,
    CARGO_TYPE_LABELS,
    CERTIFICATION_LABELS,
)


def nav_row() -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton("⬅️ Назад", callback_data="truck:back"),
        InlineKeyboardButton("❌ Отмена", callback_data="truck:cancel"),
    ]


def with_nav(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([*rows, nav_row()])


def body_type_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("Тент", callback_data="truck:body:tent"),
            InlineKeyboardButton("Реф", callback_data="truck:body:refrigerator"),
        ],
        [
            InlineKeyboardButton("Открытый", callback_data="truck:body:open"),
            InlineKeyboardButton("Контейнер", callback_data="truck:body:container"),
        ],
        [InlineKeyboardButton("Любой", callback_data="truck:body:any")],
    ]
    return with_nav(rows)


def multi_select_keyboard(
    prefix: str,
    options: dict[str, str],
    selected: set[str],
    done_label: str = "✅ Готово",
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for key, label in options.items():
        mark = "✅" if key in selected else "⬜️"
        rows.append([InlineKeyboardButton(f"{mark} {label}", callback_data=f"truck:{prefix}:toggle:{key}")])
    rows.append([InlineKeyboardButton(done_label, callback_data=f"truck:{prefix}:done")])
    return with_nav(rows)


def certifications_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    return multi_select_keyboard("cert", CERTIFICATION_LABELS, selected)


def cargo_types_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    return multi_select_keyboard("cargo", CARGO_TYPE_LABELS, selected)


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Сохранить", callback_data="truck:confirm:save"),
                InlineKeyboardButton("✏️ Изменить", callback_data="truck:confirm:edit"),
            ],
            nav_row(),
        ]
    )


def text_step_keyboard() -> InlineKeyboardMarkup:
    return with_nav([])
