"""TPS Service — Third-party app integration, OAuth, token management.

Run with: uvicorn services.tps.main:app --port 8001 --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import SQLModel

from services.tps.config import settings
from services.tps.deps import get_engine
from services.tps.models import AppMarketplace

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


async def seed_marketplace(engine):
    """Seed the app marketplace with default entries."""
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlmodel import select

    async with AsyncSession(engine) as db:
        stmt = select(AppMarketplace).where(AppMarketplace.app_name == "github")
        result = await db.exec(stmt)

        if not result.first():
            github = AppMarketplace(
                app_name="github",
                display_name="GitHub",
                auth_type="oauth2",
                authorize_url="https://github.com/login/oauth/authorize",
                token_url="https://github.com/login/oauth/access_token",
                scopes="read:user user:email repo",
                icon_url="https://github.githubassets.com/favicons/favicon-dark.svg",
            )
            db.add(github)
            await db.commit()
            logger.info("Seeded GitHub in app marketplace")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and seed marketplace on startup."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    await seed_marketplace(engine)
    logger.info("TPS service started — tables created")
    yield
    logger.info("TPS service shutting down")


app = FastAPI(
    title="GenAlpha TPS",
    description="Third-party app integration, OAuth, and token management",
    version="0.1.0",
    lifespan=lifespan,
)

# Register routes
from services.tps.routes.apps import router as apps_router
from services.tps.routes.integrations import router as integrations_router

app.include_router(apps_router)
app.include_router(integrations_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "tps"}
