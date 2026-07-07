from playwright.async_api import async_playwright

from core.config import Settings
from core.logger import logger

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class PlaywrightFetcher:
    """Headless browser fetch (аналог PhantomJS/CasperJS для JS-сайтов)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_html(
        self,
        url: str,
        *,
        locale: str = "ru-RU",
        cookie: str | None = None,
        wait_selector: str | None = None,
    ) -> str:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self._settings.playwright_headless)
            context = await browser.new_context(user_agent=DEFAULT_USER_AGENT, locale=locale)
            if cookie:
                await context.add_cookies(_parse_cookie_header(cookie, url))

            page = await context.new_page()
            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self._settings.playwright_timeout_ms,
                )
                if wait_selector:
                    try:
                        await page.wait_for_selector(wait_selector, timeout=15000)
                    except Exception as exc:
                        logger.debug("Selector %s not found: %s", wait_selector, exc)
                else:
                    await page.wait_for_timeout(2000)
                return await page.content()
            finally:
                await browser.close()


def _parse_cookie_header(cookie_header: str, url: str) -> list[dict]:
    from urllib.parse import urlparse

    host = urlparse(url).hostname or ""
    cookies = []
    for part in cookie_header.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        cookies.append({"name": name.strip(), "value": value.strip(), "domain": host, "path": "/"})
    return cookies
