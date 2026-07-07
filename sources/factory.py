from core.config import Settings, get_settings
from sources.ati_su import AtiSuSource
from sources.base import BaseSource
from sources.deliver_kz import DeliverKzSource


def build_sources(settings: Settings | None = None) -> list[BaseSource]:
    settings = settings or get_settings()
    sources: list[BaseSource] = [
        AtiSuSource(settings),
        DeliverKzSource(settings),
    ]
    if settings.enable_demo_source:
        from sources.demo_source import DemoSource

        sources.append(DemoSource(settings))
    return sources
