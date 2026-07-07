import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from core.logger import logger
from models.schemas import CargoRequestCreate
from sources.base import BaseSource
from sources.hybrid_fetcher import HybridFetcher
from sources.parsing import (
    extract_inline_json_objects,
    extract_route,
    find_cargo_records,
    map_record_to_fields,
    parse_float,
)

SOURCE_NAME = "ati_su"
DISPLAY_NAME = "ATI.SU"

CARD_SELECTORS = (
    "[data-testid='load-item']",
    ".load-item",
    "[class*='LoadItem']",
    "[class*='load-card']",
    "[class*='cargo-item']",
    "article",
)


class AtiSuSource(BaseSource):
    name = SOURCE_NAME
    display_name = DISPLAY_NAME

    def __init__(self, settings=None) -> None:
        super().__init__(settings)
        self._fetcher = HybridFetcher(self.settings)

    async def fetch(self) -> str:
        if self.settings.ati_su_api_url:
            payload = await self._fetcher.fetch_json(
                self.settings.ati_su_api_url,
                cookie=self.settings.ati_su_cookie or None,
            )
            if payload is not None:
                import json

                return json.dumps(payload, ensure_ascii=False)

        return await self._fetcher.fetch_html(
            self.settings.ati_su_url,
            cookie=self.settings.ati_su_cookie or None,
            locale="ru-RU",
            wait_selector=", ".join(CARD_SELECTORS[:3]),
        )

    def parse(self, raw_html: str) -> list[CargoRequestCreate]:
        json_payload = HybridFetcher.try_parse_json_text(raw_html)
        if json_payload is not None:
            from_json = self._parse_from_json(json_payload)
            if from_json:
                return from_json

        results = self._parse_html_cards(raw_html)
        if results:
            return results

        return self._parse_inline_json(raw_html)

    def _parse_from_json(self, payload: dict | list) -> list[CargoRequestCreate]:
        records = find_cargo_records(payload)
        results: list[CargoRequestCreate] = []
        for record in records:
            item = self._record_to_request(record)
            if item:
                results.append(item)
        return results

    def _parse_html_cards(self, raw_html: str) -> list[CargoRequestCreate]:
        soup = BeautifulSoup(raw_html, "lxml")
        results: list[CargoRequestCreate] = []

        cards: list = []
        for selector in CARD_SELECTORS:
            cards = soup.select(selector)
            if cards:
                break

        for card in cards:
            try:
                parsed = self._parse_card(card)
                if parsed:
                    results.append(parsed)
            except Exception as exc:
                logger.debug("[ati_su] Card parse error: %s", exc)
        return results

    def _parse_inline_json(self, raw_html: str) -> list[CargoRequestCreate]:
        results: list[CargoRequestCreate] = []
        for obj in extract_inline_json_objects(raw_html):
            for record in find_cargo_records(obj):
                item = self._record_to_request(record)
                if item:
                    results.append(item)
        return results

    def _record_to_request(self, record: dict) -> CargoRequestCreate | None:
        fields = map_record_to_fields(record)
        if not fields.get("origin_city") or not fields.get("destination_city"):
            return None

        rate = fields.get("rate_amount")
        distance = fields.get("distance_km")
        rate_per_km = round(rate / distance, 1) if rate and distance else None

        return CargoRequestCreate(
            external_id=fields.get("external_id"),
            source=SOURCE_NAME,
            origin_city=fields["origin_city"],
            destination_city=fields["destination_city"],
            distance_km=distance,
            rate_amount=rate,
            rate_currency="₽",
            rate_per_km=rate_per_km,
            cargo_description=fields.get("cargo_description"),
            cargo_weight_tons=fields.get("cargo_weight_tons"),
            cargo_volume_m3=fields.get("cargo_volume_m3"),
            loading_date=fields.get("loading_date"),
            company_name=fields.get("company_name"),
            source_url=fields.get("source_url"),
        )

    def _parse_card(self, card) -> CargoRequestCreate | None:
        text = card.get_text(" ", strip=True)
        if len(text) < 20:
            return None

        route_el = (
            card.select_one("[class*='route']")
            or card.select_one("[data-testid='route']")
            or card.select_one("a[href*='load']")
        )
        route_text = route_el.get_text(" ", strip=True) if route_el else text[:120]
        origin, destination, distance = extract_route(route_text)
        if not origin or not destination:
            return None

        rate_el = card.select_one("[class*='rate'], [class*='price'], [class*='Rate']")
        rate_text = rate_el.get_text(" ", strip=True) if rate_el else ""
        rate_amount = parse_float(rate_text)
        per_km_match = re.search(r"(\d[\d\s]*)\s*₽?\s*/\s*км", text, re.IGNORECASE)
        rate_per_km = parse_float(per_km_match.group(1)) if per_km_match else None

        cargo_el = card.select_one("[class*='cargo'], [class*='Cargo'], [class*='goods']")
        cargo_text = cargo_el.get_text(" ", strip=True) if cargo_el else ""
        weight_match = re.search(r"(\d+(?:[.,]\d+)?)\s*т", text, re.IGNORECASE)
        volume_match = re.search(r"(\d+(?:[.,]\d+)?)\s*м[³3]", text, re.IGNORECASE)

        date_el = card.select_one("[class*='date'], [class*='loading'], time")
        loading_date = date_el.get_text(" ", strip=True) if date_el else None
        time_match = re.search(r"(\d{1,2}:\d{2})", text)
        loading_time = time_match.group(1) if time_match else None

        company_el = card.select_one("[class*='company'], [class*='firm'], [class*='owner']")
        company_name = company_el.get_text(" ", strip=True) if company_el else None
        rating_match = re.search(r"(\d(?:[.,]\d+)?)\s*(?:⭐|★|балл)", text)
        company_rating = parse_float(rating_match.group(1)) if rating_match else None

        link = card.select_one("a[href]")
        source_url = urljoin(self.settings.ati_su_url, link["href"]) if link and link.get("href") else None
        external_id = None
        if source_url:
            id_match = re.search(r"/(\d{5,})", source_url)
            external_id = id_match.group(1) if id_match else None

        return CargoRequestCreate(
            external_id=external_id,
            source=SOURCE_NAME,
            origin_city=origin,
            destination_city=destination,
            distance_km=distance,
            rate_amount=rate_amount,
            rate_currency="₽",
            rate_per_km=rate_per_km,
            cargo_description=cargo_text or None,
            cargo_weight_tons=parse_float(weight_match.group(1)) if weight_match else None,
            cargo_volume_m3=parse_float(volume_match.group(1)) if volume_match else None,
            loading_date=loading_date,
            loading_time=loading_time,
            company_name=company_name,
            company_rating=company_rating,
            source_url=source_url,
        )
