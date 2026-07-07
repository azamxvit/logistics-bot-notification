from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import get_settings
from core.logger import logger
from models.db_models import Base

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=settings.database_ssl_args,
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    logger.info("Connecting to database at %s", settings.database_host_label)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        logger.error(
            "Database connection failed (%s). "
            "На Railway: Variables → DATABASE_URL → Add Reference → cargobot-db → DATABASE_URL",
            exc,
        )
        raise

    from core.migrations import run_migrations

    await run_migrations(engine)
    logger.info("Database ready")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
