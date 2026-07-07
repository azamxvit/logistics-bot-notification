from datetime import datetime, timezone

from models.schemas import CargoRequestCreate
from sources.base import BaseSource

SOURCE_NAME = "demo"
DISPLAY_NAME = "DEMO"


class DemoSource(BaseSource):
    """
    Тестовый источник — отдаёт реалистичные заявки без парсинга бирж.
    Включить: ENABLE_DEMO_SOURCE=true
    """

    name = SOURCE_NAME
    display_name = DISPLAY_NAME

    async def fetch(self) -> str:
        return "demo"

    def parse(self, raw_html: str) -> list[CargoRequestCreate]:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        return [
            CargoRequestCreate(
                external_id=f"demo-ati-{stamp}",
                source="ati_su",
                origin_city="Алматы",
                destination_city="Астана",
                distance_km=1270,
                rate_amount=380_000,
                rate_currency="₸",
                rate_per_km=299,
                cargo_description="Стройматериалы",
                cargo_weight_tons=18,
                cargo_volume_m3=82,
                loading_date=datetime.now(timezone.utc).strftime("%d.%m"),
                loading_time="09:00",
                company_name="ООО Строй Логистика",
                company_rating=4.7,
            ),
            CargoRequestCreate(
                external_id=f"demo-deliver-{stamp}",
                source="deliver_kz",
                origin_city="Шымкент",
                destination_city="Алматы",
                distance_km=680,
                rate_amount=210_000,
                rate_currency="₸",
                rate_per_km=309,
                cargo_description="Продукты питания",
                cargo_type="perishable_food",
                cargo_weight_tons=12,
                cargo_volume_m3=45,
                loading_date=datetime.now(timezone.utc).strftime("%d.%m"),
                loading_time="14:00",
                company_name="ТОО Agro Trans",
                company_rating=4.5,
            ),
        ]
