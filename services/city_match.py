"""Сопоставление городов по названию (без GPS и радиуса в км)."""


def city_matches(request_city: str, filter_city: str) -> bool:
    """Проверить, что города совпадают по названию (подстрока в обе стороны).

    Примеры:
    - «Алматы» ↔ «Алматы» ✓
    - «Атырау» ↔ «Индер» ✗ (разные города)
    - «Экибастуз г-к» ↔ «Экибастуз» ✓
    """
    if not request_city or not filter_city:
        return False
    a = request_city.strip().lower()
    b = filter_city.strip().lower()
    return b in a or a in b


def cities_match_any(request_city: str, filter_cities: list[str]) -> bool:
    return any(city_matches(request_city, c) for c in filter_cities)
