"""App marketplace controller — implements AppsApi interface.

Routes only handle HTTP concerns. Uses generated DTOs from OpenAPI specs.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from services.tps.api.generated.apps_models import AppMarketplaceDTO, AppMeta
from services.tps.deps import DbDep, TpsAuthDep
from services.tps.models import AppMarketplace, AuthType, AppCategory, AppProvider

router = APIRouter(prefix="/apps", tags=["apps"])


def _serialize_app(app: AppMarketplace) -> AppMarketplaceDTO:
    """Serialize an AppMarketplace entity to the generated DTO."""
    return AppMarketplaceDTO(
        id=app.id,
        app_code=app.app_code,
        app_name=app.app_name,
        display_name=app.display_name,
        auth_type=AuthType(app.auth_type).label,
        category=AppCategory(app.category).label,
        provider=AppProvider(app.provider).label,
        meta=AppMeta(**(app.meta or {})),
        is_install_required=app.is_install_required,
    )


@router.get("", response_model=list[AppMarketplaceDTO])
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


@router.get("/{identifier}", response_model=AppMarketplaceDTO)
async def get_app(identifier: str, db: DbDep, _auth: TpsAuthDep):
    """GET /apps/{identifier} — polymorphic lookup by app_name or app_code."""
    if identifier.isdigit():
        stmt = select(AppMarketplace).where(AppMarketplace.app_code == int(identifier))
    else:
        stmt = select(AppMarketplace).where(AppMarketplace.app_name == identifier)

    result = await db.exec(stmt)
    app = result.first()
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{identifier}' not found")
    return _serialize_app(app)
