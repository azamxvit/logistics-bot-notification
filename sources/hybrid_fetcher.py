import json

from core.config import Settings
from core.logger import logger
from sources.http_fetcher import HttpFetcher
from sources.playwright_fetcher import PlaywrightFetcher


class HybridFetcher:
    """
    Стратегия загрузки:
    1. aiohttp (curl) — быстро, если HTML/JSON отдаётся сразу
    2. Playwright — если страница JS-driven
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._http = HttpFetcher(settings)
        self._browser = PlaywrightFetcher(settings)

    async def fetch_html(
        self,
        url: str,
        *,
        cookie: str | None = None,
        locale: str = "ru-RU",
        wait_selector: str | None = None,
        min_html_size: int = 1500,
    ) -> str:
        try:
            html = await self._http.get_text(url, cookie=cookie)
            if len(html) >= min_html_size:
                logger.info("Fetched %s via HTTP (%d bytes)", url, len(html))
                return html
            logger.info("HTTP response too small for %s, fallback to Playwright", url)
        except Exception as exc:
            logger.info("HTTP fetch failed for %s: %s — fallback to Playwright", url, exc)

        html = await self._browser.get_html(
            url,
            cookie=cookie,
            locale=locale,
            wait_selector=wait_selector,
        )
        logger.info("Fetched %s via Playwright (%d bytes)", url, len(html))
        return html

    async def fetch_json(
        self,
        url: str,
        *,
        cookie: str | None = None,
    ) -> dict | list | None:
        try:
            return await self._http.get_json(url, cookie=cookie)
        except Exception as exc:
            logger.debug("JSON API fetch failed for %s: %s", url, exc)
            return None

    @staticmethod
    def try_parse_json_text(text: str) -> dict | list | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
