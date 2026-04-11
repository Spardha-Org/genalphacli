"""TPS Service — Third-party app integration, OAuth, token management.

Run with: uvicorn services.tps.main:app --port 8001 --reload
Migrations: alembic upgrade head (run before starting)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """TPS startup — Alembic handles schema, no create_all needed."""
    logger.info("TPS service started — run 'alembic upgrade head' to apply migrations")
    yield
    logger.info("TPS service shutting down")


app = FastAPI(
    title="GenAlpha TPS",
    description="Third-party app integration, OAuth, and token management",
    version="0.2.0",
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
