from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import CargoRequest
from models.schemas import CargoRequestCreate
from services.cargo_classifier import detect_cargo_type


class RequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_hash(self, content_hash: str) -> CargoRequest | None:
        result = await self._session.execute(
            select(CargoRequest).where(CargoRequest.content_hash == content_hash)
        )
        return result.scalar_one_or_none()

    async def create(self, data: CargoRequestCreate, content_hash: str) -> CargoRequest:
        request = CargoRequest(
            external_id=data.external_id,
            source=data.source,
            origin_city=data.origin_city,
            destination_city=data.destination_city,
            distance_km=data.distance_km,
            rate_amount=data.rate_amount,
            rate_currency=data.rate_currency,
            rate_per_km=data.rate_per_km,
            cargo_description=data.cargo_description,
            cargo_type=detect_cargo_type(data.cargo_description, data.cargo_type),
            cargo_weight_tons=data.cargo_weight_tons,
            cargo_volume_m3=data.cargo_volume_m3,
            body_type=data.body_type,
            loading_date=data.loading_date,
            loading_time=data.loading_time,
            company_name=data.company_name,
            company_rating=data.company_rating,
            content_hash=content_hash,
            source_url=data.source_url,
        )
        self._session.add(request)
        await self._session.commit()
        await self._session.refresh(request)
        return request
