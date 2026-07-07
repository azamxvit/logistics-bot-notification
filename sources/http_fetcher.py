import aiohttp

from core.config import Settings
from core.logger import logger

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}


class HttpFetcher:
    """Curl-like HTTP fetcher (aiohttp) with optional cookie auth."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_text(
        self,
        url: str,
        *,
        cookie: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> str:
        headers = {**DEFAULT_HEADERS, **(extra_headers or {})}
        if cookie:
            headers["Cookie"] = cookie

        timeout = aiohttp.ClientTimeout(total=self._settings.playwright_timeout_ms / 1000)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.get(url, allow_redirects=True) as response:
                response.raise_for_status()
                text = await response.text()
                logger.debug("HTTP GET %s -> %s (%d bytes)", url, response.status, len(text))
                return text

    async def get_json(
        self,
        url: str,
        *,
        cookie: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict | list:
        headers = {**DEFAULT_HEADERS, "Accept": "application/json", **(extra_headers or {})}
        if cookie:
            headers["Cookie"] = cookie

        timeout = aiohttp.ClientTimeout(total=self._settings.playwright_timeout_ms / 1000)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.get(url, allow_redirects=True) as response:
                response.raise_for_status()
                return await response.json()
