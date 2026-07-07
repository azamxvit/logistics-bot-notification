from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from core.config import get_settings
from core.logger import logger
from models.db_models import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
            connect_args=settings.database_ssl_args,
        )
    return _engine


def async_session_factory() -> AsyncSession:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _session_factory()


async def init_db() -> None:
    settings = get_settings()
    logger.info("Connecting to database at %s", settings.database_host_label)
    try:
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        logger.error(
            "Database connection failed (%s). "
            "На Railway: сервис cargobot → Variables → Add Reference → cargobot-db → DATABASE_URL → Deploy",
            exc,
        )
        raise

    from core.migrations import run_migrations

    await run_migrations(get_engine())
    logger.info("Database ready")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
