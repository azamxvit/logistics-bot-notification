from models.db_models import CargoType

_HAZARDOUS_KEYWORDS = (
    "адр", "опасн", "взрыво", "химическ", "горюч", "токсич", "радиоактив",
)
_FRAGILE_KEYWORDS = ("хрупк", "стекл", "хрупкий", "бьющ", "керамик")
_PERISHABLE_KEYWORDS = (
    "продукт", "скоропорт", "мяс", "молоч", "овощ", "пищев", "рыб",
    "фрукт", "замороз", "реф", "temperature",
)


def detect_cargo_type(description: str | None, explicit: str | None = None) -> str:
    if explicit and explicit in {c.value for c in CargoType}:
        return explicit
    if not description:
        return CargoType.GENERAL.value

    text = description.lower()
    if any(keyword in text for keyword in _HAZARDOUS_KEYWORDS):
        return CargoType.HAZARDOUS.value
    if any(keyword in text for keyword in _PERISHABLE_KEYWORDS):
        return CargoType.PERISHABLE_FOOD.value
    if any(keyword in text for keyword in _FRAGILE_KEYWORDS):
        return CargoType.FRAGILE.value
    return CargoType.GENERAL.value


def cargo_requires_certification(cargo_type: str) -> set[str]:
    if cargo_type == CargoType.HAZARDOUS.value:
        return {"adr"}
    return set()
