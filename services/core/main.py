"""Core Service — Platform auth, user management, business logic.

Run with: uvicorn services.core.main:app --port 8000 --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle. Schema managed by Alembic (make migrate)."""
    logger.info("Core service started")
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
from services.core.routes.integrations import router as integrations_router
from services.core.routes.parse import router as parse_router
from services.core.routes.parse_pypi import router as parse_pypi_router
from services.core.routes.generate import router as generate_router
from services.core.routes.publish import router as publish_router
from services.core.routes.artifacts import router as artifacts_router
from services.core.routes.oauth_callback import router as oauth_callback_router

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(services_router)
app.include_router(integrations_router)
app.include_router(parse_router)
app.include_router(parse_pypi_router)
app.include_router(generate_router)
app.include_router(publish_router)
app.include_router(artifacts_router)
app.include_router(oauth_callback_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "core"}
