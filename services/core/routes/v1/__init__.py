"""API v1 routes — thin controllers that delegate to services."""

from fastapi import APIRouter

from services.core.routes.v1 import auth, projects, services, parse, generate, integrations, artifacts, internal, oauth_callback

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(projects.router)
router.include_router(services.router)
router.include_router(parse.router)
router.include_router(generate.router)
router.include_router(integrations.router)
router.include_router(artifacts.router)
router.include_router(internal.router)
router.include_router(oauth_callback.router)
