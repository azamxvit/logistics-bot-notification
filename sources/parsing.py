import json
import re
from typing import Any

from bs4 import BeautifulSoup

ROUTE_PATTERN = re.compile(
    r"(.+?)\s*(?:→|->|—|–|-)\s*(.+?)(?:\s*\((\d[\d\s]*)\s*км\))?$",
    re.IGNORECASE,
)


def parse_float(text: str | None) -> float | None:
    if not text:
        return None
    cleaned = re.sub(r"[^\d.,]", "", text.replace(",", "."))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def extract_route(text: str) -> tuple[str, str, float | None]:
    match = ROUTE_PATTERN.search(text.strip())
    if not match:
        return "", "", None
    origin = match.group(1).strip()
    destination = match.group(2).strip()
    distance = parse_float(match.group(3).replace(" ", "")) if match.group(3) else None
    return origin, destination, distance


def extract_inline_json_objects(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    objects: list[dict[str, Any]] = []

    for script in soup.find_all("script"):
        script_type = (script.get("type") or "").lower()
        content = script.string or script.get_text() or ""
        if not content.strip():
            continue

        if script_type in {"application/json", "application/ld+json"}:
            parsed = _safe_json_load(content)
            if parsed:
                objects.append(parsed)
            continue

        for match in re.finditer(r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})", content):
            parsed = _safe_json_load(match.group(1))
            if parsed and _looks_like_cargo_payload(parsed):
                objects.append(parsed)

        next_data = re.search(r"__NEXT_DATA__\s*=\s*(\{.+?\})\s*;?\s*</script>", content, re.DOTALL)
        if next_data:
            parsed = _safe_json_load(next_data.group(1))
            if parsed:
                objects.append(parsed)

        state_match = re.search(
            r"(?:window\.)?(?:__INITIAL_STATE__|__PRELOADED_STATE__)\s*=\s*(\{.+?\});",
            content,
            re.DOTALL,
        )
        if state_match:
            parsed = _safe_json_load(state_match.group(1))
            if parsed:
                objects.append(parsed)

    return objects


def find_cargo_records(payload: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    _walk_payload(payload, records)
    return records


def _walk_payload(node: Any, records: list[dict[str, Any]]) -> None:
    if isinstance(node, dict):
        if _looks_like_cargo_record(node):
            records.append(node)
        for value in node.values():
            _walk_payload(value, records)
    elif isinstance(node, list):
        for item in node:
            _walk_payload(item, records)


def _looks_like_cargo_payload(node: Any) -> bool:
    if not isinstance(node, dict):
        return False
    keys = {k.lower() for k in node}
    route_keys = {"from", "to", "origin", "destination", "fromcity", "tocity", "loadingcity", "unloadingcity"}
    return len(keys & route_keys) >= 2


def _looks_like_cargo_record(node: dict[str, Any]) -> bool:
    keys = {k.lower() for k in node}
    route_pairs = [
        ("from", "to"),
        ("origin", "destination"),
        ("fromcity", "tocity"),
        ("loadingcity", "unloadingcity"),
        ("cityfrom", "cityto"),
    ]
    for left, right in route_pairs:
        if left in keys and right in keys:
            return True
    if "origin_city" in keys and "destination_city" in keys:
        return True
    return False


def map_record_to_fields(record: dict[str, Any]) -> dict[str, Any]:
    def pick(*names: str) -> Any:
        for name in names:
            for key, value in record.items():
                if key.lower() == name.lower() and value not in (None, ""):
                    return value
        return None

    origin = pick("from", "origin", "fromCity", "loadingCity", "cityFrom", "origin_city")
    destination = pick("to", "destination", "toCity", "unloadingCity", "cityTo", "destination_city")
    rate = pick("rate", "price", "cost", "rate_amount", "sum")
    weight = pick("weight", "tonnage", "cargo_weight", "cargo_weight_tons", "mass")
    volume = pick("volume", "cargo_volume", "cargo_volume_m3")
    distance = pick("distance", "distance_km", "km")
    cargo = pick("cargo", "cargo_description", "goods", "cargoName", "description")
    load_date = pick("loading_date", "loadDate", "date", "loadingDate")
    company = pick("company", "company_name", "firm", "customer")
    external_id = pick("id", "external_id", "loadId", "cargo_id")
    url = pick("url", "link", "source_url", "href")

    return {
        "external_id": str(external_id) if external_id is not None else None,
        "origin_city": str(origin).strip() if origin else None,
        "destination_city": str(destination).strip() if destination else None,
        "rate_amount": parse_float(str(rate)) if rate is not None else None,
        "cargo_weight_tons": parse_float(str(weight)) if weight is not None else None,
        "cargo_volume_m3": parse_float(str(volume)) if volume is not None else None,
        "distance_km": parse_float(str(distance)) if distance is not None else None,
        "cargo_description": str(cargo).strip() if cargo else None,
        "loading_date": str(load_date).strip() if load_date else None,
        "company_name": str(company).strip() if company else None,
        "source_url": str(url).strip() if url else None,
    }


def _safe_json_load(raw: str) -> dict[str, Any] | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
