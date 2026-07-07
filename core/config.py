import ssl
from functools import lru_cache
from urllib.parse import parse_qs, urlparse, urlunparse

from pydantic import Field, field_validator
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

    # Railway public proxy и облачные Postgres требуют SSL
    needs_ssl = (
        host.endswith(".proxy.rlwy.net")
        or host.endswith(".render.com")
        or "sslmode" in query
        or query.get("sslmode", [""])[0] == "require"
    )
    if needs_ssl:
        return {"ssl": ssl.create_default_context()}

    return {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str = ""

    database_url_env: str | None = Field(default=None, alias="DATABASE_URL")
    redis_url_env: str | None = Field(default=None, alias="REDIS_URL")

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
    ati_su_api_url: str = ""
    ati_su_cookie: str = ""
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
    def database_url(self) -> str:
        if self.database_url_env:
            return _to_asyncpg_url(self.database_url_env)
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_ssl_args(self) -> dict:
        source = self.database_url_env or self.database_url
        return database_connect_args(source)

    @property
    def redis_url(self) -> str:
        if self.redis_url_env:
            return self.redis_url_env
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def database_host_label(self) -> str:
        if self.database_url_env:
            return urlparse(self.database_url_env).hostname or "unknown"
        return self.postgres_host


@lru_cache
def get_settings() -> Settings:
    return Settings()
