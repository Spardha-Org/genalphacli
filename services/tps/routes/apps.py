"""App marketplace routes."""

from __future__ import annotations

from fastapi import APIRouter
from sqlmodel import select

from services.tps.deps import DbDep, TpsAuthDep
from services.tps.models import AppMarketplace

router = APIRouter(prefix="/apps", tags=["apps"])


@router.get("")
async def list_apps(db: DbDep, _auth: TpsAuthDep):
    """List all available apps in the marketplace."""
    stmt = select(AppMarketplace).where(AppMarketplace.active == True)
    result = await db.exec(stmt)
    apps = result.all()

    return [
        {
            "id": app.id,
            "app_name": app.app_name,
            "display_name": app.display_name,
            "auth_type": app.auth_type,
            "icon_url": app.icon_url,
        }
        for app in apps
    ]
