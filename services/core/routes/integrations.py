"""Integration routes — uses TPS SDK (direct function calls, no HTTP)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.core.deps import CurrentUserDep, DbDep
from services.core.tps_client import tps

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ── Apps ──


@router.get("/apps")
async def list_apps(db: DbDep, user: CurrentUserDep):
    """List available apps from TPS marketplace."""
    return await tps.list_apps(db)


@router.get("/apps/{identifier}")
async def get_app(identifier: str, db: DbDep, user: CurrentUserDep):
    """Get a single app by name or code."""
    app = await tps.get_app(db, identifier)
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{identifier}' not found")
    return app


# ── Integrations ──


@router.get("")
async def list_integrations(db: DbDep, user: CurrentUserDep):
    """List connected integrations for this user."""
    return await tps.list_integrations(db, user.id)


@router.get("/{identifier}")
async def get_integration(identifier: str, db: DbDep, user: CurrentUserDep):
    """Get a single integration by app_name or integration_id."""
    integration = await tps.get_integration(db, user.id, identifier)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration


# ── OAuth Flow ──


class InstallRequest(BaseModel):
    form_data: dict | None = None


@router.post("/{app_name}/install")
async def install_app(
    app_name: str, db: DbDep, user: CurrentUserDep, body: InstallRequest | None = None,
):
    """Start OAuth flow — returns authorize URL."""
    from services.tps.config import settings
    redirect_uri = settings.github_redirect_uri  # TODO: per-app redirect URIs
    try:
        return await tps.start_oauth_install(
            db, user.id, app_name, redirect_uri,
            form_data=body.form_data if body else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class ExchangeRequest(BaseModel):
    code: str
    state: str


@router.post("/{app_name}/exchange")
async def exchange_oauth_code(
    app_name: str, body: ExchangeRequest, db: DbDep, user: CurrentUserDep,
):
    """Exchange OAuth code+state for token."""
    from services.tps.config import settings
    redirect_uri = settings.github_redirect_uri
    try:
        return await tps.exchange_oauth_code(
            db, user.id, app_name, body.code, body.state, redirect_uri,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Credential Flow ──


class ConnectRequest(BaseModel):
    credentials: dict


@router.post("/{app_name}/connect")
async def connect_app(
    app_name: str, body: ConnectRequest, db: DbDep, user: CurrentUserDep,
):
    """Connect a credential-based app."""
    try:
        return await tps.connect_credentials(db, user.id, app_name, body.credentials)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Delete ──


@router.delete("/{integration_id}")
async def delete_integration(integration_id: str, db: DbDep, user: CurrentUserDep):
    """Disconnect an integration."""
    deleted = await tps.delete_integration(db, integration_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {"ok": True}
