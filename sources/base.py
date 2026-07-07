from abc import ABC, abstractmethod

from core.config import Settings, get_settings
from core.logger import logger
from models.schemas import CargoRequestCreate


class BaseSource(ABC):
    name: str = "base"
    display_name: str = "Unknown"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @abstractmethod
    async def fetch(self) -> str:
        """Fetch raw HTML from the source."""

    @abstractmethod
    def parse(self, raw_html: str) -> list[CargoRequestCreate]:
        """Parse raw HTML into structured cargo requests."""

    async def run(self) -> list[CargoRequestCreate]:
        attempts = self.settings.source_retry_attempts
        delay = self.settings.source_retry_delay_sec

        for attempt in range(1, attempts + 1):
            try:
                logger.info("[%s] Fetching (attempt %d/%d)", self.name, attempt, attempts)
                raw = await self.fetch()
                requests = self.parse(raw)
                logger.info("[%s] Parsed %d requests", self.name, len(requests))
                return requests
            except Exception as exc:
                logger.error("[%s] Attempt %d failed: %s", self.name, attempt, exc, exc_info=True)
                if attempt < attempts:
                    import asyncio

                    await asyncio.sleep(delay * attempt)

        logger.warning("[%s] All attempts failed, returning empty list", self.name)
        return []
