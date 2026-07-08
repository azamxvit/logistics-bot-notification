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
    # --- Мультифуры: до 3 профилей на пользователя ---
    """
    ALTER TABLE truck_profiles
    DROP CONSTRAINT IF EXISTS truck_profiles_user_id_key
    """,
    """
    ALTER TABLE truck_profiles
    ADD COLUMN IF NOT EXISTS label VARCHAR(100) NOT NULL DEFAULT 'Фура'
    """,
    """
    ALTER TABLE truck_profiles
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT false
    """,
    """
    ALTER TABLE truck_profiles
    ADD COLUMN IF NOT EXISTS search_until TIMESTAMPTZ
    """,
    # Существующие профили считаем активными бессрочно (обратная совместимость)
    """
    UPDATE truck_profiles
    SET is_active = true
    WHERE is_active = false AND search_until IS NULL AND label = 'Фура'
    """,
    """
    UPDATE truck_profiles
    SET label = 'Фура 1'
    WHERE label = 'Фура'
    """,
]


async def run_migrations(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for sql in MIGRATIONS:
            await conn.execute(text(sql.strip()))
    logger.info("Database migrations applied")
