from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.db_models import MAX_TRUCKS_PER_USER, TruckProfile, User
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
            .options(selectinload(User.truck_profiles))
        )
        return list(result.scalars().unique().all())


class TruckRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_telegram_id(self, telegram_user_id: int) -> list[TruckProfile]:
        result = await self._session.execute(
            select(TruckProfile)
            .join(User)
            .where(User.telegram_user_id == telegram_user_id)
            .order_by(TruckProfile.id)
        )
        return list(result.scalars().all())

    async def count_by_telegram_id(self, telegram_user_id: int) -> int:
        return len(await self.list_by_telegram_id(telegram_user_id))

    async def get_by_id(self, profile_id: int, telegram_user_id: int) -> TruckProfile | None:
        result = await self._session.execute(
            select(TruckProfile)
            .join(User)
            .where(
                TruckProfile.id == profile_id,
                User.telegram_user_id == telegram_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self, telegram_user_id: int, data: TruckProfileData
    ) -> TruckProfile:
        result = await self._session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {telegram_user_id} not found")

        current = await self.count_by_telegram_id(telegram_user_id)
        if current >= MAX_TRUCKS_PER_USER:
            raise ValueError("truck_limit_reached")

        profile = TruckProfile(
            user_id=user.id,
            label=data.label,
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

    async def update(
        self, profile_id: int, telegram_user_id: int, data: TruckProfileData
    ) -> TruckProfile | None:
        profile = await self.get_by_id(profile_id, telegram_user_id)
        if not profile:
            return None

        profile.label = data.label
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
        await self._session.commit()
        await self._session.refresh(profile)
        return profile

    async def delete(self, profile_id: int, telegram_user_id: int) -> bool:
        profile = await self.get_by_id(profile_id, telegram_user_id)
        if not profile:
            return False
        await self._session.delete(profile)
        await self._session.commit()
        return True

    async def set_search_window(
        self, profile_id: int, telegram_user_id: int, days: int
    ) -> TruckProfile | None:
        profile = await self.get_by_id(profile_id, telegram_user_id)
        if not profile:
            return None
        profile.is_active = True
        profile.search_until = datetime.now(timezone.utc) + timedelta(days=days)
        await self._session.commit()
        await self._session.refresh(profile)
        return profile

    async def get_active_profiles(self) -> list[TruckProfile]:
        """Активные фуры с непросроченным окном поиска (для рассылки)."""
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            select(TruckProfile)
            .options(selectinload(TruckProfile.user))
            .where(
                TruckProfile.is_active.is_(True),
                TruckProfile.search_until.isnot(None),
                TruckProfile.search_until > now,
            )
        )
        return list(result.scalars().all())

    async def get_expired_profiles(self) -> list[TruckProfile]:
        """Активные фуры, у которых окно поиска истекло (для деактивации)."""
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            select(TruckProfile)
            .options(selectinload(TruckProfile.user))
            .where(
                TruckProfile.is_active.is_(True),
                TruckProfile.search_until.isnot(None),
                TruckProfile.search_until <= now,
            )
        )
        return list(result.scalars().all())

    async def deactivate(self, profile_id: int) -> None:
        result = await self._session.execute(
            select(TruckProfile).where(TruckProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            profile.is_active = False
            await self._session.commit()
