"""App marketplace routes."""

from __future__ import annotations

from fastapi import APIRouter
from sqlmodel import select

from services.tps.deps import DbDep, TpsAuthDep
from services.tps.models import AppMarketplace, AuthType, AppCategory, AppProvider

router = APIRouter(prefix="/apps", tags=["apps"])


@router.get("")
async def list_apps(db: DbDep, _auth: TpsAuthDep):
    """List all available apps in the marketplace with full metadata."""
    stmt = select(AppMarketplace).where(AppMarketplace.active == True)  # noqa: E712
    result = await db.exec(stmt)
    apps = result.all()

    return [
        {
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
        for app in apps
    ]
