import os
import ssl
from functools import lru_cache
from urllib.parse import parse_qs, quote_plus, urlparse, urlunparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _to_asyncpg_url(url: str) -> str:
    if "+asyncpg" not in url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(url)
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        params.pop("sslmode", None)
        new_query = "&".join(f"{k}={v[0]}" for k, v in params.items() if v and v[0])
        url = urlunparse(parsed._replace(query=new_query))

    return url


def database_connect_args(url: str) -> dict:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    query = parse_qs(parsed.query)

    if host in {"localhost", "127.0.0.1", "postgres"}:
        return {}

    needs_ssl = (
        host.endswith(".proxy.rlwy.net")
        or host.endswith(".render.com")
        or "sslmode" in query
        or query.get("sslmode", [""])[0] == "require"
    )
    if needs_ssl:
        return {"ssl": ssl.create_default_context()}

    return {}


def _env(*names: str) -> str | None:
    """Первое непустое значение из переменных окружения."""
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str = ""

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "cargobot"
    postgres_password: str = "cargobot"
    postgres_db: str = "cargobot"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    scheduler_interval_min: int = 10
    scheduler_interval_max: int = 20
    source_retry_attempts: int = 3
    source_retry_delay_sec: int = 5

    ati_su_url: str = "https://loads.ati.su/"
    ati_su_api_url: str = "https://loads.ati.su/webapi/v1.0/loads/search"
    ati_su_cookie: str = ""
    # Автологин через Playwright (получает cookie сам, не протухает)
    ati_su_login: str = ""
    ati_su_password: str = ""
    ati_su_login_url: str = "https://id.ati.su/login/"
    ati_su_session_ttl_min: int = 60
    # Гео-ID бирж ATI: 50 = Китай, 10 = Казахстан (type 0 = страна)
    ati_su_from_geo_id: int = 50
    ati_su_to_geo_id: int = 10
    ati_su_items_per_page: int = 10
    # Полный JSON payload (переопределяет from/to), если задан
    ati_su_search_payload: str = ""

    deliver_kz_url: str = "https://deliver.kz/ru/cargo"
    deliver_kz_api_url: str = ""
    deliver_kz_cookie: str = ""

    enable_demo_source: bool = False

    playwright_headless: bool = True
    playwright_timeout_ms: int = 60000

    log_level: str = "INFO"

    @field_validator("enable_demo_source", mode="before")
    @classmethod
    def parse_bool(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @property
    def is_railway(self) -> bool:
        return bool(_env("RAILWAY_ENVIRONMENT", "RAILWAY_SERVICE_ID", "RAILWAY_PROJECT_ID"))

    @property
    def raw_database_url(self) -> str | None:
        return _env("DATABASE_URL", "DATABASE_PRIVATE_URL", "DATABASE_PUBLIC_URL")

    @property
    def database_url(self) -> str:
        raw = self.raw_database_url
        if raw:
            return _to_asyncpg_url(raw)

        pg_host = _env("PGHOST")
        if pg_host:
            user = quote_plus(_env("PGUSER") or "postgres")
            password = quote_plus(_env("PGPASSWORD") or "")
            port = _env("PGPORT") or "5432"
            database = _env("PGDATABASE") or "railway"
            return f"postgresql+asyncpg://{user}:{password}@{pg_host}:{port}/{database}"

        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def has_database_config(self) -> bool:
        return bool(self.raw_database_url or _env("PGHOST")) or not self.is_railway

    @property
    def database_ssl_args(self) -> dict:
        source = self.raw_database_url or self.database_url
        return database_connect_args(source)

    @property
    def redis_url(self) -> str:
        raw = _env("REDIS_URL", "REDIS_PRIVATE_URL", "REDIS_PUBLIC_URL")
        if raw:
            return raw
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def has_redis_config(self) -> bool:
        return bool(_env("REDIS_URL", "REDIS_PRIVATE_URL", "REDIS_PUBLIC_URL")) or not self.is_railway

    @property
    def database_host_label(self) -> str:
        return urlparse(self.database_url).hostname or "unknown"

    @property
    def ati_su_payload(self) -> dict:
        import json

        if self.ati_su_search_payload.strip():
            try:
                return json.loads(self.ati_su_search_payload)
            except json.JSONDecodeError:
                pass

        return {
            "filter": {
                "from": {"id": self.ati_su_from_geo_id, "type": 0, "exact_only": True},
                "to": {"id": self.ati_su_to_geo_id, "type": 0, "exact_only": True},
                "dates": {"dateOption": "today-plus"},
                "extraParams": 0,
                "sortingType": 2,
                "boardList": [],
                "cargoTypes": [],
                "excludeTenders": False,
            },
            "exclude_geo_dicts": True,
            "page": 1,
            "items_per_page": self.ati_su_items_per_page,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
