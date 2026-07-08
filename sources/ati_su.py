import json
from datetime import datetime
from typing import Any

import aiohttp

from core.logger import logger
from models.schemas import CargoRequestCreate
from sources import ati_auth
from sources.base import BaseSource
from sources.http_fetcher import HttpFetcher

SOURCE_NAME = "ati_su"
DISPLAY_NAME = "ATI.SU"

# Валюты ATI по id (поле rate.currency)
CURRENCY_SYMBOLS = {
    0: "",
    1: "₽",
    2: "$",
    3: "€",
    4: "Br",
    21: "₸",
    23: "₸",
}


def _parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%d.%m")
    except ValueError:
        return None


class AtiSuSource(BaseSource):
    name = SOURCE_NAME
    display_name = DISPLAY_NAME

    def __init__(self, settings=None) -> None:
        super().__init__(settings)
        self._http = HttpFetcher(self.settings)

    async def fetch(self) -> str:
        payload = self.settings.ati_su_payload
        cookie = await ati_auth.get_cookie(self.settings)
        if not cookie:
            logger.warning(
                "[ati_su] Нет cookie ATI. "
                "Задайте ATI_SU_COOKIE или ATI_SU_LOGIN/ATI_SU_PASSWORD."
            )

        try:
            data = await self._http.post_json(
                self.settings.ati_su_api_url,
                payload,
                cookie=cookie,
            )
        except aiohttp.ClientResponseError as exc:
            if exc.status not in (401, 403):
                raise

            logger.warning("[ati_su] Сессия ATI истекла (%s), пробую перелогин", exc.status)
            ati_auth.invalidate()
            fresh_cookie = await ati_auth.get_cookie(self.settings, force=True)
            if not fresh_cookie:
                raise

            data = await self._http.post_json(
                self.settings.ati_su_api_url,
                payload,
                cookie=fresh_cookie,
            )
        return json.dumps(data, ensure_ascii=False)

    def parse(self, raw: str) -> list[CargoRequestCreate]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("[ati_su] Ответ не является JSON")
            return []

        loads = data.get("loads") if isinstance(data, dict) else None
        if not loads:
            logger.info("[ati_su] В ответе нет заявок (loads пуст)")
            return []

        results: list[CargoRequestCreate] = []
        for item in loads:
            try:
                parsed = self._parse_load(item)
                if parsed:
                    results.append(parsed)
            except Exception as exc:
                logger.debug("[ati_su] Ошибка разбора заявки: %s", exc)
        return results

    def _parse_load(self, item: dict[str, Any]) -> CargoRequestCreate | None:
        loading = item.get("loading") or {}
        unloading = item.get("unloading") or {}
        origin = (loading.get("location") or {}).get("city")
        destination = (unloading.get("location") or {}).get("city")
        if not origin or not destination:
            return None

        route = item.get("route") or {}
        distance = route.get("distance") or None

        load = item.get("load") or {}
        weight = load.get("weight") or None
        volume = load.get("volume") or None
        cargo_desc = load.get("cargoType") or None
        adr = load.get("adr") or 0
        cargo_type = "hazardous" if adr and adr > 0 else None

        rate_amount, currency = self._extract_rate(item.get("rate") or {})
        rate_per_km = None
        if rate_amount and distance:
            rate_per_km = round(rate_amount / distance, 1)

        firm = item.get("firm") or {}
        company_name = firm.get("name") or None
        company_rating = (firm.get("rating") or {}).get("score")

        external_id = item.get("id")
        source_url = f"https://loads.ati.su/gruz/{external_id}" if external_id else None

        loading_date = _parse_date(loading.get("firstDate"))
        loading_time = (loading.get("time") or "").strip() or None

        return CargoRequestCreate(
            external_id=str(external_id) if external_id else None,
            source=SOURCE_NAME,
            origin_city=origin.strip(),
            destination_city=destination.strip(),
            distance_km=float(distance) if distance else None,
            rate_amount=float(rate_amount) if rate_amount else None,
            rate_currency=currency,
            rate_per_km=rate_per_km,
            cargo_description=cargo_desc,
            cargo_type=cargo_type,
            cargo_weight_tons=float(weight) if weight else None,
            cargo_volume_m3=float(volume) if volume else None,
            loading_date=loading_date,
            loading_time=loading_time,
            company_name=company_name,
            company_rating=float(company_rating) if company_rating else None,
            source_url=source_url,
        )

    def _extract_rate(self, rate: dict[str, Any]) -> tuple[float | None, str]:
        currency_id = rate.get("currency", 0)
        currency = CURRENCY_SYMBOLS.get(currency_id, "")

        amount: float | None = None
        for key in ("priceNds", "priceNoNds", "price"):
            value = rate.get(key)
            if value:
                amount = value
                break

        if amount is None:
            rates_with_vat = rate.get("ratesWithVat") or []
            if rates_with_vat:
                amount = rates_with_vat[0].get("rateWithVat")

        return (amount or None), currency
