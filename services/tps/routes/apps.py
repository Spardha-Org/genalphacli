"""App marketplace routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from services.tps.deps import DbDep, TpsAuthDep
from services.tps.models import AppMarketplace, AuthType, AppCategory, AppProvider


def _serialize_app(app: AppMarketplace) -> dict:
    return {
        "id": app.id,
        "app_code": app.app_code,
        "app_name": app.app_name,
        "display_name": app.display_name,
        "auth_type": AuthType(app.auth_type).label,
        "category": AppCategory(app.category).label,
        "provider": AppProvider(app.provider).label,
        "meta": app.meta,
        "is_install_required": app.is_install_required,
    }

router = APIRouter(prefix="/apps", tags=["apps"])


@router.get("")
async def list_apps(db: DbDep, _auth: TpsAuthDep):
    """List all available apps in the marketplace with full metadata."""
    stmt = select(AppMarketplace).where(AppMarketplace.active == True)  # noqa: E712
    result = await db.exec(stmt)
    apps = result.all()

    return [_serialize_app(app) for app in apps]


@router.get("/{app_name}")
async def get_app(app_name: str, db: DbDep, _auth: TpsAuthDep):
    """Get a single app by name."""
    result = await db.exec(
        select(AppMarketplace).where(AppMarketplace.app_name == app_name)
    )
    app = result.first()
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{app_name}' not found")
    return _serialize_app(app)
