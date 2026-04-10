"""Integration routes — OAuth install, callback, management."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import select

from services.tps.config import settings
from services.tps.deps import DbDep, TpsAuthDep, WorkspaceIdDep
from services.tps.handlers import get_handler
from services.tps.integration_service import (
    create_integration,
    delete_integration,
    get_or_refresh,
)
from services.tps.models import Integration, OAuthState

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/{app_name}/install")
async def install_app(
    app_name: str,
    db: DbDep,
    workspace_id: WorkspaceIdDep,
    _auth: TpsAuthDep,
):
    """Start the OAuth installation flow. Returns the authorization URL."""
    try:
        handler = get_handler(app_name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"App '{app_name}' not found")

    redirect_uri = settings.github_redirect_uri
    authorize_url, state = handler.get_authorize_url(redirect_uri)

    # Persist state in DB (survives process restarts / uvicorn reload)
    oauth_state = OAuthState(state=state, workspace_id=workspace_id, app_name=app_name)
    db.add(oauth_state)
    await db.commit()

    return {
        "authorize_url": authorize_url,
        "state": state,
    }


class ExchangeRequest(BaseModel):
    code: str
    state: str


@router.post("/{app_name}/exchange")
async def exchange_oauth_code(
    app_name: str,
    body: ExchangeRequest,
    db: DbDep,
    workspace_id: WorkspaceIdDep,
    _auth: TpsAuthDep,
):
    """Exchange OAuth code+state for token. Called by Core (not browser).

    Validates state from DB, exchanges code for token, encrypts and stores.
    """
    # Look up state from DB (CSRF protection)
    stmt = select(OAuthState).where(OAuthState.state == body.state)
    result = await db.exec(stmt)
    oauth_state = result.first()

    if not oauth_state:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    if oauth_state.app_name != app_name:
        raise HTTPException(status_code=400, detail="App name mismatch")

    # Delete the used state (single-use)
    await db.delete(oauth_state)
    await db.commit()

    try:
        handler = get_handler(app_name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"App '{app_name}' not found")

    # Exchange code for token
    redirect_uri = settings.github_redirect_uri
    try:
        config = await handler.exchange_code(body.code, redirect_uri)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Fetch user info for display
    user_info = await handler.get_user_info(config)

    # Store encrypted integration
    integration = await create_integration(
        db,
        workspace_id=workspace_id,
        app_name=app_name,
        config=config,
        github_username=user_info.get("login"),
    )

    logger.info(
        "Integration created: %s for workspace %s (user: %s)",
        integration.id,
        workspace_id,
        user_info.get("login"),
    )

    return {
        "integration_id": integration.id,
        "app_name": app_name,
        "username": user_info.get("login"),
        "status": "active",
    }


@router.get("")
async def list_integrations(
    db: DbDep,
    workspace_id: WorkspaceIdDep,
    _auth: TpsAuthDep,
):
    """List all integrations for a workspace."""
    stmt = select(Integration).where(
        Integration.workspace_id == workspace_id,
        Integration.status == "active",
    )
    result = await db.exec(stmt)
    integrations = result.all()

    return [
        {
            "id": i.id,
            "app_name": i.app_name,
            "github_username": i.github_username,
            "status": i.status,
            "created_at": i.created_at.isoformat(),
        }
        for i in integrations
    ]


@router.delete("/{integration_id}")
async def remove_integration(
    integration_id: str,
    db: DbDep,
    workspace_id: WorkspaceIdDep,
    _auth: TpsAuthDep,
):
    """Disconnect an integration."""
    deleted = await delete_integration(db, integration_id, workspace_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")

    return {"ok": True}


class CloneRequest(BaseModel):
    repo_url: str


@router.post("/{integration_id}/clone")
async def clone_repo_with_integration(
    integration_id: str,
    body: CloneRequest,
    db: DbDep,
    workspace_id: WorkspaceIdDep,
    _auth: TpsAuthDep,
):
    """Clone a repo using the integration's credentials."""
    config = await get_or_refresh(db, integration_id, workspace_id)
    access_token = config.get("access_token")

    if not access_token:
        raise HTTPException(status_code=401, detail="No access token available")

    from genalphacli.github import clone_repo, fetch_repo_info, parse_github_url

    owner, repo = parse_github_url(body.repo_url)
    info = fetch_repo_info(owner, repo, token=access_token)
    clone_dir = clone_repo(info, token=access_token)

    return {
        "clone_dir": str(clone_dir),
        "owner": owner,
        "repo": repo,
    }
