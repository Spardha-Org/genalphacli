"""Core Service — Platform auth, user management, business logic.

Run with: uvicorn services.core.main:app --port 8000 --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import SQLModel

from services.core.config import settings
from services.core.deps import get_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("Core service started — tables created")
    yield
    logger.info("Core service shutting down")


app = FastAPI(
    title="GenAlpha Core",
    description="Platform auth, user management, and business logic",
    version="0.1.0",
    lifespan=lifespan,
)

# Register routes
from services.core.auth.routes import router as auth_router
from services.core.routes.projects import router as projects_router
from services.core.routes.services import router as services_router

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(services_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "core"}
