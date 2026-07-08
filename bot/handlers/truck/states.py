(
    MENU,
    TONNAGE,
    VOLUME,
    BODY_TYPE,
    CERTIFICATIONS,
    CARGO_TYPES,
    MIN_RATE,
    ORIGINS,
    DESTINATIONS,
    CONFIRM,
    SEARCH_WINDOW,
    LOCATION_CITY,
) = range(12)

# Карта «Назад» внутри мастера настройки
PREVIOUS_STATE: dict[int, int | None] = {
    TONNAGE: MENU,
    VOLUME: TONNAGE,
    BODY_TYPE: VOLUME,
    CERTIFICATIONS: BODY_TYPE,
    CARGO_TYPES: CERTIFICATIONS,
    MIN_RATE: CARGO_TYPES,
    ORIGINS: MIN_RATE,
    DESTINATIONS: ORIGINS,
    CONFIRM: DESTINATIONS,
}

BODY_TYPE_LABELS: dict[str, str] = {
    "tent": "Тент",
    "refrigerator": "Рефрижератор",
    "open": "Открытый",
    "container": "Контейнер",
    "any": "Любой",
}

CERTIFICATION_LABELS: dict[str, str] = {
    "adr": "ADR (опасные грузы)",
}

CARGO_TYPE_LABELS: dict[str, str] = {
    "hazardous": "Опасные / взрывоопасные",
    "fragile": "Хрупкие",
    "perishable_food": "Продукты / скоропорт",
    "general": "Обычный груз",
}

SKIP_TEXTS = {"-", "—", "нет", "пропустить", "любые"}
