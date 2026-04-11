"""Integration routes — uses TPS SDK (direct function calls, own DB connection)."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.core.config import settings
from services.core.deps import CurrentUserDep
from services.core.oauth_state import OAuthState, encode_state
from services.core.tps_client import tps

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ── Apps ──


@router.get("/apps")
async def list_apps(user: CurrentUserDep):
    return await tps.list_apps()


@router.get("/apps/{identifier}")
async def get_app(identifier: str, user: CurrentUserDep):
    app = await tps.get_app(identifier)
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{identifier}' not found")
    return app


# ── Integrations ──


@router.get("")
async def list_integrations(user: CurrentUserDep):
    return await tps.list_integrations(user.id)


@router.get("/{identifier}")
async def get_integration(identifier: str, user: CurrentUserDep):
    integration = await tps.get_integration(user.id, identifier)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration


# ── OAuth Flow ──


class InstallRequest(BaseModel):
    callback_path: str = "/integrations"
    form_data: dict | None = None


@router.post("/{app_name}/install")
async def install_app(app_name: str, body: InstallRequest, user: CurrentUserDep):
    """Start OAuth flow. Core generates encrypted state, TPS builds the URL."""
    state = OAuthState(
        user_id=user.id,
        app_name=app_name,
        timestamp=time.time(),
        callback_path=body.callback_path,
        form_data=body.form_data,
    )
    encoded_state = encode_state(state)
    redirect_uri = f"{settings.app_url}/api/oauth/callback"

    try:
        return await tps.build_oauth_url(app_name, encoded_state, redirect_uri, body.form_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Credential Flow ──


class ConnectRequest(BaseModel):
    credentials: dict


@router.post("/{app_name}/connect")
async def connect_app(app_name: str, body: ConnectRequest, user: CurrentUserDep):
    try:
        return await tps.connect_credentials(user.id, app_name, body.credentials)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Delete ──


@router.delete("/{integration_id}")
async def delete_integration(integration_id: str, user: CurrentUserDep):
    deleted = await tps.delete_integration(integration_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {"ok": True}
