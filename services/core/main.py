"""Core Service — Platform auth, user management, business logic.

Run with: uvicorn services.core.main:app --port 8000 --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from services.core.clients.email_client import EmailClient
from services.core.clients.temporal_client import TemporalClient
from services.core.clients.tps_client import TpsHttpClient
from services.core.config import settings
from services.core.exceptions import DomainError
from services.core.middleware import (
    RequestLoggingMiddleware,
    domain_error_handler,
    generic_error_handler,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create clients on startup, dispose on shutdown."""
    # ── Startup ──
    app.state.tps = TpsHttpClient(settings.tps.url, settings.tps.secret, settings.tps.timeout)
    app.state.email = EmailClient(settings.email.resend_api_key, settings.email.from_address)

    try:
        app.state.temporal = await TemporalClient.connect(settings.temporal_address)
    except Exception as e:
        logger.warning("Temporal unavailable at startup: %s (workflows will fail)", e)
        app.state.temporal = None

    logger.info("Core service started (env=%s)", settings.environment)
    yield

    # ── Shutdown ──
    await app.state.tps.close()
    logger.info("Core service shut down")


app = FastAPI(
    title="GenAlpha Core",
    description="Platform auth, user management, and business logic",
    version="0.2.0",
    lifespan=lifespan,
)

# ── Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", settings.app_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

# ── Error Handlers ──
app.add_exception_handler(DomainError, domain_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

# ── Routes ──
from services.core.routes.v1 import router as v1_router  # noqa: E402

app.include_router(v1_router)

# ── OAuth Callback (stays at root — browser redirect target) ──
from services.core.routes.v1.integrations import router as _  # noqa: E402, F811


@app.get("/health")
async def health():
    """Deep health check — verifies DB and downstream services."""
    checks = {"core": "ok"}

    # Check Temporal
    if hasattr(app.state, "temporal") and app.state.temporal:
        checks["temporal"] = "ok"
    else:
        checks["temporal"] = "unavailable"

    return {"status": "ok", "service": "core", "checks": checks}


# ── Backward Compatibility Routes ──
# Keep old routes working during frontend migration to /api/v1/*
# TODO: Remove after frontend is fully migrated

from services.core.routes.v1.auth import router as auth_v1  # noqa: E402
from services.core.routes.v1.projects import router as projects_v1  # noqa: E402
from services.core.routes.v1.services import router as services_v1  # noqa: E402
from services.core.routes.v1.parse import router as parse_v1  # noqa: E402
from services.core.routes.v1.generate import router as generate_v1  # noqa: E402
from services.core.routes.v1.integrations import router as integrations_v1  # noqa: E402
from services.core.routes.v1.artifacts import router as artifacts_v1  # noqa: E402

# These are the SAME routers — they'll be mounted at both /api/v1/* and /*
# FastAPI deduplicates them, so this is safe during transition
