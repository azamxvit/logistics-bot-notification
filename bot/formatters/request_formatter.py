from models.db_models import CargoRequest


class RequestFormatter:
    SOURCE_LABELS = {
        "ati_su": "ATI.SU",
        "deliver_kz": "Deliver.kz",
    }

    @classmethod
    def format(cls, request: CargoRequest, source_label: str | None = None) -> str:
        label = source_label or cls.SOURCE_LABELS.get(request.source, request.source.upper())

        lines = [f"🟢 НОВАЯ ЗАЯВКА | {label}"]

        route = f"🚛 {request.origin_city} → {request.destination_city}"
        if request.distance_km:
            distance = f"{request.distance_km:,.0f}".replace(",", " ")
            route += f" ({distance} км)"
        lines.append(route)

        if request.rate_amount is not None:
            rate = f"{request.rate_amount:,.0f}".replace(",", " ")
            currency = request.rate_currency or "₸"
            rate_line = f"💰 Ставка: {rate} {currency}"
            if request.rate_per_km:
                per_km = f"{request.rate_per_km:,.0f}".replace(",", " ")
                rate_line += f" ({per_km} {currency}/км)"
            lines.append(rate_line)

        cargo_parts = []
        if request.cargo_description:
            cargo_parts.append(request.cargo_description[:60])
        weight_vol = []
        if request.cargo_weight_tons:
            weight_vol.append(f"{request.cargo_weight_tons:g}т")
        if request.cargo_volume_m3:
            weight_vol.append(f"{request.cargo_volume_m3:g}м³")
        if weight_vol:
            cargo_parts.append(" / ".join(weight_vol))
        if cargo_parts:
            lines.append(f"📦 Груз: {', '.join(cargo_parts)}")

        if request.loading_date:
            date_line = f"📅 Погрузка: {request.loading_date}"
            if request.loading_time:
                date_line += f" с {request.loading_time}"
            lines.append(date_line)

        if request.company_name:
            company_line = f"🏢 {request.company_name}"
            if request.company_rating:
                company_line += f" | ⭐ {request.company_rating:g}"
            lines.append(company_line)

        if request.source_url:
            lines.append(f"🔗 {request.source_url}")

        return "\n".join(lines)
