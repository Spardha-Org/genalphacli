"""Integration controller — implements IntegrationsApi interface.

Routes only handle HTTP concerns. Uses generated DTOs from OpenAPI specs.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from services.tps.api.generated.integrations_models import (
    ConnectRequest,
    ConnectResponse,
    ExchangeRequest,
    InstallRequest,
    InstallResponse,
    IntegrationDTO,
    OkResponse,
)
from services.tps.config import settings
from services.tps.deps import DbDep, TpsAuthDep, WorkspaceIdDep
from services.tps.handlers import get_handler, get_oauth_handler, get_credential_handler
from services.tps.handlers.base import OAuthHandler
from services.tps.integration_service import (
    cleanup_expired_states,
    create_integration,
    delete_integration,
)
from services.tps.models import AppMarketplace, Integration, OAuthState

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])


# ── OAuth Flow ──


@router.post("/{app_name}/install", response_model=InstallResponse)
async def install_app(
    app_name: str,
    db: DbDep,
    workspace_id: WorkspaceIdDep,
    _auth: TpsAuthDep,
    body: InstallRequest | None = None,
):
    """Start the OAuth installation flow. Returns the authorization URL.

    For Form-based OAuth2 apps, body.form_data contains user-provided fields
    (e.g., tenant URL) needed to construct the authorize URL.
    """
    # Validate app exists and requires install
    app_result = await db.exec(
        select(AppMarketplace).where(AppMarketplace.app_name == app_name, AppMarketplace.active == True)  # noqa: E712
    )
    app = app_result.first()
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{app_name}' not found")
    if not app.is_install_required:
        raise HTTPException(status_code=400, detail=f"App '{app_name}' uses credential flow, not OAuth install")

    try:
        handler = get_oauth_handler(app_name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"No handler for app: {app_name}")

    # Clean up expired states while we're here
    await cleanup_expired_states(db)

    # Build redirect URI — generic callback, not per-app
    redirect_uri = settings.github_redirect_uri  # TODO: make generic per-app
    form_data = body.form_data if body else None
    authorize_url, state = handler.get_authorize_url(redirect_uri, form_data)

    # Persist state in DB with form_data for Form-based OAuth2
    oauth_state = OAuthState(
        state=state,
        workspace_id=workspace_id,
        app_name=app_name,
        meta=form_data,
    )
    db.add(oauth_state)
    await db.commit()

    return InstallResponse(authorize_url=authorize_url, state=state)


@router.post("/{app_name}/exchange", response_model=ConnectResponse)
async def exchange_oauth_code(
    app_name: str,
    body: ExchangeRequest,
    db: DbDep,
    workspace_id: WorkspaceIdDep,
    _auth: TpsAuthDep,
):
    """Exchange OAuth code+state for token. Validates state, stores encrypted token."""
    # Look up and validate state
    stmt = select(OAuthState).where(OAuthState.state == body.state)
    result = await db.exec(stmt)
    oauth_state = result.first()

    if not oauth_state:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    if oauth_state.app_name != app_name:
        raise HTTPException(status_code=400, detail="App name mismatch")

    # Delete the used state (single-use)
    form_data = oauth_state.meta
    await db.delete(oauth_state)
    await db.commit()

    try:
        handler = get_oauth_handler(app_name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"No handler for app: {app_name}")

    # Exchange code for token
    redirect_uri = settings.github_redirect_uri  # TODO: make generic per-app
    try:
        config = await handler.exchange_code(body.code, redirect_uri, form_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Token exchange failed for %s: %s", app_name, e)
        raise HTTPException(status_code=500, detail="Token exchange failed")

    # Fetch user info for display
    try:
        user_info = await handler.get_user_info(config)
    except Exception as e:
        logger.warning("Failed to fetch user info for %s: %s", app_name, e)
        user_info = {}

    # Store encrypted integration
    identifier = user_info.get("login") or user_info.get("email")
    expires_at = config.get("expires_at")

    integration = await create_integration(
        db,
        workspace_id=workspace_id,
        app_name=app_name,
        config=config,
        identifier=identifier,
        expires_at=expires_at,
    )

    return ConnectResponse(
        integration_id=integration.id,
        app_name=app_name,
        identifier=identifier,
        status="active",
    )


# ── Credential Flow (API Key, Basic Auth, mTLS) ──


@router.post("/{app_name}/connect", response_model=ConnectResponse)
async def connect_app(
    app_name: str,
    body: ConnectRequest,
    db: DbDep,
    workspace_id: WorkspaceIdDep,
    _auth: TpsAuthDep,
):
    """Connect a credential-based app (API Key, Basic Auth, mTLS).

    Credentials are validated, encrypted, and stored.
    """
    # Validate app exists and does NOT require install
    app_result = await db.exec(
        select(AppMarketplace).where(AppMarketplace.app_name == app_name, AppMarketplace.active == True)  # noqa: E712
    )
    app = app_result.first()
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{app_name}' not found")
    if app.is_install_required:
        raise HTTPException(status_code=400, detail=f"App '{app_name}' uses OAuth flow, not credential connect")

    # Validate required fields from meta
    form_fields = app.meta.get("form_fields", [])
    for field in form_fields:
        if field.get("required") and field["reference_key"] not in body.credentials:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field['display_name']}",
            )

    # Optional: validate credentials with the handler
    try:
        handler = get_credential_handler(app_name)
        is_valid = await handler.validate_credentials(body.credentials)
        if not is_valid:
            raise HTTPException(status_code=400, detail="Credentials are invalid")
    except ValueError:
        # No handler — store credentials without validation
        pass

    # Store encrypted integration
    integration = await create_integration(
        db,
        workspace_id=workspace_id,
        app_name=app_name,
        config=body.credentials,
        identifier=body.credentials.get("email") or body.credentials.get("username"),
    )

    return ConnectResponse(
        integration_id=integration.id,
        app_name=app_name,
        identifier=integration.identifier,
        status="active",
    )


# ── List / Delete ──


@router.get("", response_model=list[IntegrationDTO])
async def list_integrations(
    db: DbDep,
    workspace_id: WorkspaceIdDep,
    _auth: TpsAuthDep,
):
    """List all active integrations for a workspace."""
    stmt = select(Integration).where(
        Integration.workspace_id == workspace_id,
        Integration.status == "active",
    )
    result = await db.exec(stmt)
    return [
        IntegrationDTO(
            id=i.id,
            app_name=i.app_name,
            identifier=i.identifier,
            status=i.status,
            created_at=i.created_at.isoformat(),
        )
        for i in result.all()
    ]


@router.delete("/{integration_id}", response_model=OkResponse)
async def remove_integration(
    integration_id: str,
    db: DbDep,
    workspace_id: WorkspaceIdDep,
    _auth: TpsAuthDep,
):
    """Disconnect an integration — revokes token and wipes credentials."""
    deleted = await delete_integration(db, integration_id, workspace_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")
    return OkResponse(ok=True)
