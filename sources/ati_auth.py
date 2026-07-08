"""Автологин на ATI.SU через Playwright.

Открывает форму входа id.ati.su, вводит логин/пароль, забирает cookie сессии
и кэширует его в памяти. Cookie переиспользуется между циклами сбора и
перезапрашивается по TTL или принудительно (при 401/403 от API).
"""

import time

from playwright.async_api import async_playwright

from core.config import Settings
from core.logger import logger

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Модульный кэш, чтобы не логиниться на каждом цикле планировщика
_CACHE: dict[str, object] = {"cookie": None, "ts": 0.0}


async def get_cookie(settings: Settings, *, force: bool = False) -> str | None:
    """Вернуть cookie сессии ATI. Логинится при необходимости.

    Приоритет: ручной ATI_SU_COOKIE > кэш > свежий логин.
    """
    if settings.ati_su_cookie and not force:
        return settings.ati_su_cookie

    if not (settings.ati_su_login and settings.ati_su_password):
        return settings.ati_su_cookie or None

    ttl_sec = settings.ati_su_session_ttl_min * 60
    cached = _CACHE.get("cookie")
    ts = float(_CACHE.get("ts") or 0.0)
    if cached and not force and (time.time() - ts) < ttl_sec:
        return str(cached)

    cookie = await _login(settings)
    if cookie:
        _CACHE["cookie"] = cookie
        _CACHE["ts"] = time.time()
    return cookie


def invalidate() -> None:
    _CACHE["cookie"] = None
    _CACHE["ts"] = 0.0


async def _login(settings: Settings) -> str | None:
    logger.info("[ati_auth] Логинюсь на ATI.SU через Playwright...")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=settings.playwright_headless)
        context = await browser.new_context(user_agent=DEFAULT_USER_AGENT, locale="ru-RU")
        page = await context.new_page()
        try:
            await page.goto(
                settings.ati_su_login_url,
                wait_until="domcontentloaded",
                timeout=settings.playwright_timeout_ms,
            )

            await _dismiss_cookie_banner(page)

            login_field = page.get_by_placeholder("Логин")
            password_field = page.get_by_placeholder("Пароль")
            await login_field.wait_for(timeout=15000)
            await login_field.fill(settings.ati_su_login)
            await password_field.fill(settings.ati_su_password)

            # Отправка формы: сначала Enter, затем клик по кнопке как фолбэк
            await password_field.press("Enter")
            try:
                await page.get_by_role("button", name="Войти").click(timeout=5000)
            except Exception:
                pass

            try:
                await page.wait_for_url("**ati.su/**", timeout=20000)
            except Exception:
                await page.wait_for_load_state("networkidle", timeout=20000)
            await page.wait_for_timeout(2000)

            cookies = await context.cookies()
            cookie_header = _build_cookie_header(cookies)
            if not cookie_header or "sid=" not in cookie_header:
                logger.error("[ati_auth] Не удалось получить сессию (нет sid). Проверьте логин/пароль.")
                return None

            logger.info("[ati_auth] Успешный логин, cookie получен (%d куки)", len(cookies))
            return cookie_header
        except Exception as exc:
            logger.error("[ati_auth] Ошибка логина: %s", exc, exc_info=True)
            return None
        finally:
            await browser.close()


async def _dismiss_cookie_banner(page) -> None:
    for label in ("Понятно", "ПОНЯТНО", "Все понятно", "Всё понятно"):
        try:
            btn = page.get_by_text(label, exact=False).first
            if await btn.is_visible(timeout=1500):
                await btn.click(timeout=2000)
                return
        except Exception:
            continue


def _build_cookie_header(cookies: list[dict]) -> str:
    parts = []
    for c in cookies:
        domain = (c.get("domain") or "").lstrip(".")
        if domain.endswith("ati.su"):
            parts.append(f"{c['name']}={c['value']}")
    return "; ".join(parts)
