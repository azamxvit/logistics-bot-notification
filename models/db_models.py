from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class BodyType(str, Enum):
    TENT = "tent"
    REFRIGERATOR = "refrigerator"
    OPEN = "open"
    CONTAINER = "container"
    ANY = "any"


class CargoType(str, Enum):
    HAZARDOUS = "hazardous"
    FRAGILE = "fragile"
    PERISHABLE_FOOD = "perishable_food"
    GENERAL = "general"


class Certification(str, Enum):
    ADR = "adr"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    truck_profiles: Mapped[list["TruckProfile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


# Максимум фур на одного пользователя (будет меняться в будущем)
MAX_TRUCKS_PER_USER = 3


class TruckProfile(Base):
    __tablename__ = "truck_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(100), default="Фура", server_default="Фура")
    truck_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    tonnage_tons: Mapped[float] = mapped_column(Float)
    volume_m3: Mapped[float] = mapped_column(Float)
    body_type: Mapped[str] = mapped_column(String(50), default=BodyType.ANY)
    certifications: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)), default=list, server_default="{}"
    )
    accepted_cargo_types: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)), default=lambda: [CargoType.GENERAL], server_default="{general}"
    )
    min_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_rate_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    origin_cities: Mapped[str | None] = mapped_column(Text, nullable=True)
    destination_cities: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Город, где сейчас стоит фура (геофильтр: погрузка только из этого города)
    current_city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    search_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="truck_profiles")


class CargoRequest(Base):
    __tablename__ = "cargo_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    origin_city: Mapped[str] = mapped_column(String(255))
    destination_city: Mapped[str] = mapped_column(String(255))
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    rate_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    rate_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    rate_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    cargo_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cargo_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cargo_weight_tons: Mapped[float | None] = mapped_column(Float, nullable=True)
    cargo_volume_m3: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    loading_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    loading_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
