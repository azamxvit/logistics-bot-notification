from pydantic import BaseModel, Field, field_validator

from models.db_models import CargoType, Certification


class CargoRequestCreate(BaseModel):
    external_id: str | None = None
    source: str
    origin_city: str
    destination_city: str
    distance_km: float | None = None
    rate_amount: float | None = None
    rate_currency: str | None = "₸"
    rate_per_km: float | None = None
    cargo_description: str | None = None
    cargo_type: str | None = None
    cargo_weight_tons: float | None = None
    cargo_volume_m3: float | None = None
    body_type: str | None = None
    loading_date: str | None = None
    loading_time: str | None = None
    company_name: str | None = None
    company_rating: float | None = None
    source_url: str | None = None

    def dedup_payload(self) -> dict:
        return {
            "source": self.source,
            "origin_city": self.origin_city,
            "destination_city": self.destination_city,
            "rate_amount": self.rate_amount,
            "cargo_description": self.cargo_description,
            "loading_date": self.loading_date,
            "external_id": self.external_id,
        }


class TruckProfileData(BaseModel):
    label: str = Field(default="Фура", max_length=100)
    truck_count: int = Field(default=1, ge=1)
    tonnage_tons: float = Field(gt=0)
    volume_m3: float = Field(gt=0)
    body_type: str = "any"
    certifications: list[str] = Field(default_factory=list)
    accepted_cargo_types: list[str] = Field(default_factory=lambda: [CargoType.GENERAL])
    min_rate: float | None = Field(default=None, ge=0)
    min_rate_per_km: float | None = Field(default=None, ge=0)
    origin_cities: str | None = None
    destination_cities: str | None = None

    @field_validator("certifications")
    @classmethod
    def validate_certifications(cls, value: list[str]) -> list[str]:
        allowed = {c.value for c in Certification}
        return [item for item in value if item in allowed]

    @field_validator("accepted_cargo_types")
    @classmethod
    def validate_cargo_types(cls, value: list[str]) -> list[str]:
        allowed = {c.value for c in CargoType}
        cleaned = [item for item in value if item in allowed]
        return cleaned or [CargoType.GENERAL]
