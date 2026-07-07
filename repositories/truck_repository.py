from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.db_models import TruckProfile, User
from models.schemas import TruckProfileData


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(
        self,
        telegram_user_id: int,
        username: str | None = None,
        first_name: str | None = None,
    ) -> User:
        result = await self._session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.username = username
            user.first_name = first_name
            await self._session.commit()
            return user

        user = User(
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def get_all_with_trucks(self) -> list[User]:
        result = await self._session.execute(
            select(User)
            .join(TruckProfile)
            .options(selectinload(User.truck_profile))
        )
        return list(result.scalars().unique().all())


class TruckRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_user_id: int) -> TruckProfile | None:
        result = await self._session.execute(
            select(TruckProfile)
            .join(User)
            .where(User.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, telegram_user_id: int, data: TruckProfileData) -> TruckProfile:
        result = await self._session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {telegram_user_id} not found")

        profile = await self.get_by_telegram_id(telegram_user_id)
        if profile:
            profile.truck_count = data.truck_count
            profile.tonnage_tons = data.tonnage_tons
            profile.volume_m3 = data.volume_m3
            profile.body_type = data.body_type
            profile.certifications = data.certifications
            profile.accepted_cargo_types = data.accepted_cargo_types
            profile.min_rate = data.min_rate
            profile.min_rate_per_km = data.min_rate_per_km
            profile.origin_cities = data.origin_cities
            profile.destination_cities = data.destination_cities
        else:
            profile = TruckProfile(
                user_id=user.id,
                truck_count=data.truck_count,
                tonnage_tons=data.tonnage_tons,
                volume_m3=data.volume_m3,
                body_type=data.body_type,
                certifications=data.certifications,
                accepted_cargo_types=data.accepted_cargo_types,
                min_rate=data.min_rate,
                min_rate_per_km=data.min_rate_per_km,
                origin_cities=data.origin_cities,
                destination_cities=data.destination_cities,
            )
            self._session.add(profile)

        await self._session.commit()
        await self._session.refresh(profile)
        return profile
