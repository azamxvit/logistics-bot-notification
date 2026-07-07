from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from core.logger import logger

MIGRATIONS: list[str] = [
    """
    ALTER TABLE truck_profiles
    ADD COLUMN IF NOT EXISTS truck_count INTEGER NOT NULL DEFAULT 1
    """,
    """
    ALTER TABLE truck_profiles
    ADD COLUMN IF NOT EXISTS certifications VARCHAR(50)[] NOT NULL DEFAULT '{}'
    """,
    """
    ALTER TABLE truck_profiles
    ADD COLUMN IF NOT EXISTS accepted_cargo_types VARCHAR(50)[] NOT NULL DEFAULT '{general}'
    """,
    """
    ALTER TABLE cargo_requests
    ADD COLUMN IF NOT EXISTS cargo_type VARCHAR(50)
    """,
    """
    UPDATE truck_profiles
    SET truck_count = 1
    WHERE truck_count IS NULL
    """,
    """
    UPDATE truck_profiles
    SET certifications = '{}'
    WHERE certifications IS NULL
    """,
    """
    UPDATE truck_profiles
    SET accepted_cargo_types = '{general}'
    WHERE accepted_cargo_types IS NULL
    """,
]


async def run_migrations(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for sql in MIGRATIONS:
            await conn.execute(text(sql.strip()))
    logger.info("Database migrations applied")
