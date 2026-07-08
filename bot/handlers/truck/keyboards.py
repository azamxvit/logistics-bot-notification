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


def menu_keyboard(trucks: list, can_add: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for truck in trucks:
        mark = "🟢" if getattr(truck, "is_active", False) else "⚪️"
        loc = f" | 📍{truck.current_city}" if getattr(truck, "current_city", None) else ""
        rows.append(
            [
                InlineKeyboardButton(
                    f"{mark} {truck.label} ({truck.tonnage_tons:g}т){loc}",
                    callback_data=f"truck:menu:view:{truck.id}",
                )
            ]
        )
    if can_add:
        rows.append([InlineKeyboardButton("➕ Добавить фуру", callback_data="truck:menu:add")])
    rows.append([InlineKeyboardButton("✖️ Закрыть", callback_data="truck:menu:close")])
    return InlineKeyboardMarkup(rows)


def truck_detail_keyboard(profile_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📍 Где стоит", callback_data=f"truck:menu:loc:{profile_id}"),
                InlineKeyboardButton("🔍 Время поиска", callback_data=f"truck:menu:time:{profile_id}"),
            ],
            [
                InlineKeyboardButton("✏️ Изменить", callback_data=f"truck:menu:edit:{profile_id}"),
                InlineKeyboardButton("🗑 Удалить", callback_data=f"truck:menu:del:{profile_id}"),
            ],
            [InlineKeyboardButton("⬅️ К списку", callback_data="truck:menu:list")],
        ]
    )


def search_window_keyboard(profile_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔍 1 день", callback_data=f"truck:time:set:{profile_id}:1"),
                InlineKeyboardButton("🔍 2 дня", callback_data=f"truck:time:set:{profile_id}:2"),
            ],
            [InlineKeyboardButton("⬅️ К списку", callback_data="truck:menu:list")],
        ]
    )


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
