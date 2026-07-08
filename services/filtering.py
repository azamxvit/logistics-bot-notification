from models.db_models import CargoRequest, TruckProfile
from services.cargo_classifier import cargo_requires_certification, detect_cargo_type


class FilteringService:
    BODY_TYPE_ALIASES: dict[str, set[str]] = {
        "tent": {"tent", "тент", "тентованный", "тентовый", "awning"},
        "refrigerator": {"refrigerator", "реф", "рефрижератор", "рефрижераторный", "ref"},
        "open": {"open", "открытый", "бортовой", "платформа"},
        "container": {"container", "контейнер", "контейнеровоз"},
        "any": {"any", "любой", ""},
    }

    def matches(self, request: CargoRequest, profile: TruckProfile) -> bool:
        if not self._matches_weight(request, profile):
            return False
        if not self._matches_volume(request, profile):
            return False
        if not self._matches_body_type(request, profile):
            return False
        if not self._matches_cargo_type(request, profile):
            return False
        if not self._matches_certifications(request, profile):
            return False
        if not self._matches_rate(request, profile):
            return False
        if not self._matches_route(request, profile):
            return False
        if not self._matches_current_city(request, profile):
            return False
        return True

    def _matches_current_city(self, request: CargoRequest, profile: TruckProfile) -> bool:
        """Если задан current_city — погрузка только из этого города."""
        from services.city_match import city_matches

        if not profile.current_city:
            return True
        return city_matches(request.origin_city, profile.current_city)

    def _resolve_cargo_type(self, request: CargoRequest) -> str:
        return detect_cargo_type(request.cargo_description, request.cargo_type)

    def _matches_cargo_type(self, request: CargoRequest, profile: TruckProfile) -> bool:
        cargo_type = self._resolve_cargo_type(request)
        accepted = profile.accepted_cargo_types or ["general"]
        return cargo_type in accepted

    def _matches_certifications(self, request: CargoRequest, profile: TruckProfile) -> bool:
        cargo_type = self._resolve_cargo_type(request)
        required = cargo_requires_certification(cargo_type)
        if not required:
            return True
        truck_certs = set(profile.certifications or [])
        return required.issubset(truck_certs)

    def _matches_weight(self, request: CargoRequest, profile: TruckProfile) -> bool:
        if request.cargo_weight_tons is None:
            return True
        return request.cargo_weight_tons <= profile.tonnage_tons

    def _matches_volume(self, request: CargoRequest, profile: TruckProfile) -> bool:
        if request.cargo_volume_m3 is None:
            return True
        return request.cargo_volume_m3 <= profile.volume_m3

    def _matches_body_type(self, request: CargoRequest, profile: TruckProfile) -> bool:
        if profile.body_type in ("any", ""):
            return True
        if not request.body_type:
            return True

        profile_types = self.BODY_TYPE_ALIASES.get(profile.body_type.lower(), {profile.body_type.lower()})
        request_type = request.body_type.lower()
        request_aliases = self.BODY_TYPE_ALIASES.get(request_type, {request_type})
        return bool(profile_types & request_aliases) or request_type in profile_types

    def _matches_rate(self, request: CargoRequest, profile: TruckProfile) -> bool:
        if profile.min_rate and request.rate_amount is not None:
            if request.rate_amount < profile.min_rate:
                return False
        if profile.min_rate_per_km and request.rate_per_km is not None:
            if request.rate_per_km < profile.min_rate_per_km:
                return False
        return True

    def _matches_route(self, request: CargoRequest, profile: TruckProfile) -> bool:
        if profile.origin_cities:
            origins = [c.strip().lower() for c in profile.origin_cities.split(",") if c.strip()]
            if origins and not any(o in request.origin_city.lower() for o in origins):
                return False
        if profile.destination_cities:
            destinations = [c.strip().lower() for c in profile.destination_cities.split(",") if c.strip()]
            if destinations and not any(d in request.destination_city.lower() for d in destinations):
                return False
        return True
