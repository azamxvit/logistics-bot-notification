from bot.handlers.truck.states import (
    BODY_TYPE_LABELS,
    CARGO_TYPE_LABELS,
    CERTIFICATION_LABELS,
)


def _fmt_list(items: list[str], labels: dict[str, str], empty: str = "не выбрано") -> str:
    if not items:
        return empty
    return ", ".join(labels.get(item, item) for item in items)


def prompt_truck_count(current: int | None = None) -> str:
    base = "🚛 *Настройка профиля фуры*\n\nСколько машин в автопарке?\n_Введите целое число, например: 1_"
    if current is not None:
        base += f"\n\nТекущее значение: *{current}*"
    return base


def prompt_tonnage(current: float | None = None) -> str:
    base = "Введите грузоподъёмность в тоннах.\n_Пример: 20_"
    if current is not None:
        base += f"\n\nТекущее значение: *{current:g}* т"
    return base


def prompt_volume(current: float | None = None) -> str:
    base = "Введите объём кузова в м³.\n_Пример: 82_"
    if current is not None:
        base += f"\n\nТекущее значение: *{current:g}* м³"
    return base


def prompt_body_type(current: str | None = None) -> str:
    base = "Выберите тип кузова:"
    if current:
        base += f"\n\nТекущее значение: *{BODY_TYPE_LABELS.get(current, current)}*"
    return base


def prompt_certifications(selected: set[str]) -> str:
    base = (
        "Выберите сертификации (можно несколько).\n"
        "Нажмите на пункт, чтобы переключить ✅/⬜️, затем «Готово»."
    )
    if selected:
        base += f"\n\nВыбрано: *{_fmt_list(sorted(selected), CERTIFICATION_LABELS, 'нет')}*"
    return base


def prompt_cargo_types(selected: set[str]) -> str:
    base = (
        "Какие типы грузов готовы перевозить?\n"
        "Нажмите на пункт, чтобы переключить ✅/⬜️, затем «Готово»."
    )
    if selected:
        base += f"\n\nВыбрано: *{_fmt_list(sorted(selected), CARGO_TYPE_LABELS)}*"
    else:
        base += "\n\n_Нужно выбрать хотя бы один тип._"
    return base


def prompt_min_rate(current: float | None = None) -> str:
    base = "Минимальная ставка в ₸.\n_Введите число или «-» чтобы пропустить._"
    if current is not None:
        base += f"\n\nТекущее значение: *{current:,.0f}* ₸".replace(",", " ")
    return base


def prompt_origins(current: str | None = None) -> str:
    base = "Города отправления через запятую.\n_Или «-» для любых городов._"
    if current:
        base += f"\n\nТекущее значение: *{current}*"
    return base


def prompt_destinations(current: str | None = None) -> str:
    base = "Города назначения через запятую.\n_Или «-» для любых городов._"
    if current:
        base += f"\n\nТекущее значение: *{current}*"
    return base


def build_summary(data: dict) -> str:
    certifications = _fmt_list(data.get("certifications", []), CERTIFICATION_LABELS, "нет")
    cargo_types = _fmt_list(data.get("accepted_cargo_types", []), CARGO_TYPE_LABELS)
    body = BODY_TYPE_LABELS.get(data.get("body_type", "any"), data.get("body_type", "any"))
    min_rate = data.get("min_rate")
    min_rate_text = f"{min_rate:,.0f} ₸".replace(",", " ") if min_rate else "не задана"

    return (
        "📋 *Проверьте данные профиля фуры:*\n\n"
        f"• Машин в автопарке: *{data.get('truck_count', 1)}*\n"
        f"• Грузоподъёмность: *{data.get('tonnage', 0):g}* т\n"
        f"• Объём: *{data.get('volume', 0):g}* м³\n"
        f"• Тип кузова: *{body}*\n"
        f"• Сертификации: {certifications}\n"
        f"• Типы грузов: {cargo_types}\n"
        f"• Мин. ставка: {min_rate_text}\n"
        f"• Откуда: {data.get('origins') or 'любые'}\n"
        f"• Куда: {data.get('destinations') or 'любые'}\n\n"
        "Сохранить профиль?"
    )
