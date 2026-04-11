"""App marketplace controller — implements AppsApi interface.

Routes only handle HTTP concerns (request/response). Business logic
is in the service/proxy layer.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from services.tps.deps import DbDep, TpsAuthDep
from services.tps.models import AppMarketplace, AuthType, AppCategory, AppProvider

router = APIRouter(prefix="/apps", tags=["apps"])


def _serialize_app(app: AppMarketplace) -> dict:
    """Serialize an AppMarketplace entity to the AppMarketplaceDTO response shape."""
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


@router.get("")
async def list_apps(
    db: DbDep,
    _auth: TpsAuthDep,
    category: Optional[int] = Query(None, description="Filter by category enum value"),
):
    """GET /apps — list all active apps, optionally filtered by category."""
    stmt = select(AppMarketplace).where(AppMarketplace.active == True)  # noqa: E712
    if category is not None:
        stmt = stmt.where(AppMarketplace.category == category)
    result = await db.exec(stmt)
    return [_serialize_app(app) for app in result.all()]


@router.get("/{identifier}")
async def get_app(identifier: str, db: DbDep, _auth: TpsAuthDep):
    """GET /apps/{identifier} — polymorphic lookup by app_name or app_code.

    If identifier is numeric, looks up by app_code. Otherwise by app_name.
    """
    if identifier.isdigit():
        stmt = select(AppMarketplace).where(AppMarketplace.app_code == int(identifier))
    else:
        stmt = select(AppMarketplace).where(AppMarketplace.app_name == identifier)

    result = await db.exec(stmt)
    app = result.first()
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{identifier}' not found")
    return _serialize_app(app)
