"""Core schema migrations — idempotent ALTER TABLE statements.

Core uses SQLModel's create_all for initial table creation, but create_all
doesn't add columns to existing tables. This script handles schema evolution.

Run with: uv run python -m services.core.migrate
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from services.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Each migration is an idempotent SQL statement.
# Add new columns here as the schema evolves.
MIGRATIONS = [
    # 2026-04-11: Add source_type and source_version to core_services (PyPI support)
    """
    ALTER TABLE core_services
    ADD COLUMN IF NOT EXISTS source_type VARCHAR NOT NULL DEFAULT 'github'
    """,
    """
    ALTER TABLE core_services
    ADD COLUMN IF NOT EXISTS source_version VARCHAR
    """,
]


async def run_migrations() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for migration in MIGRATIONS:
            await conn.execute(text(migration))
            logger.info("Applied: %s", migration.strip().split("\n")[1].strip())
    await engine.dispose()
    logger.info("Core migrations complete")


def main() -> None:
    asyncio.run(run_migrations())


if __name__ == "__main__":
    main()
