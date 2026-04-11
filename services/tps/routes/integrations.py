"""Integration controller — TPS is stateless for OAuth.

OAuth state is managed by Core (encrypted blob). TPS just:
- install: builds the OAuth URL with whatever state it receives
- exchange: exchanges code for token, stores integration
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from services.tps.api.generated.integrations_models import (
    ConnectRequest,
    ConnectResponse,
    IntegrationDTO,
    OkResponse,
)
from services.tps.config import settings
from services.tps.deps import DbDep, TpsAuthDep, UserIdDep
from services.tps.handlers import get_oauth_handler, get_credential_handler
from services.tps.integration_service import (
    create_integration,
    delete_integration,
)
from services.tps.models import AppMarketplace, Integration

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])


# ── OAuth Flow (TPS is stateless) ──


class InstallRequest(BaseModel):
    state: str  # Core's encrypted state blob — TPS just passes it through
    redirect_uri: str


@router.post("/{app_name}/install")
async def install_app(
    app_name: str, body: InstallRequest, db: DbDep, _auth: TpsAuthDep,
):
    """Build OAuth authorize URL. TPS is stateless — just plugs state into URL."""
    app_result = await db.exec(
        select(AppMarketplace).where(AppMarketplace.app_name == app_name, AppMarketplace.active == True)  # noqa: E712
    )
    app = app_result.first()
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{app_name}' not found")
    if not app.is_install_required:
        raise HTTPException(status_code=400, detail=f"App '{app_name}' uses credential flow")

    handler = get_oauth_handler(app_name)
    authorize_url, _ = handler.get_authorize_url(body.redirect_uri)
    # Replace handler-generated state with Core's encrypted state
    authorize_url = authorize_url.replace(
        authorize_url.split("state=")[1].split("&")[0], body.state
    )

    return {"authorize_url": authorize_url}


class ExchangeRequest(BaseModel):
    code: str
    redirect_uri: str


@router.post("/{app_name}/exchange", response_model=ConnectResponse)
async def exchange_oauth_code(
    app_name: str, body: ExchangeRequest, db: DbDep,
    user_id: UserIdDep, _auth: TpsAuthDep,
):
    """Exchange OAuth code for token. No state validation — Core already did that."""
    handler = get_oauth_handler(app_name)

    try:
        config = await handler.exchange_code(body.code, body.redirect_uri)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Token exchange failed for %s: %s", app_name, e)
        raise HTTPException(status_code=500, detail="Token exchange failed")

    try:
        user_info = await handler.get_user_info(config)
    except Exception:
        user_info = {}

    identifier = user_info.get("login") or user_info.get("email")
    expires_at = config.get("expires_at")

    integration = await create_integration(
        db, user_id=user_id, app_name=app_name,
        config=config, identifier=identifier, expires_at=expires_at,
    )

    return ConnectResponse(
        integration_id=integration.id, app_name=app_name,
        identifier=identifier, status="active",
    )


# ── Credential Flow (API Key, Basic Auth, mTLS) ──


@router.post("/{app_name}/connect", response_model=ConnectResponse)
async def connect_app(
    app_name: str, body: ConnectRequest, db: DbDep,
    user_id: UserIdDep, _auth: TpsAuthDep,
):
    """Connect a credential-based app. Validates fields, stores encrypted."""
    app_result = await db.exec(
        select(AppMarketplace).where(AppMarketplace.app_name == app_name, AppMarketplace.active == True)  # noqa: E712
    )
    app = app_result.first()
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{app_name}' not found")
    if app.is_install_required:
        raise HTTPException(status_code=400, detail=f"App '{app_name}' uses OAuth flow")

    form_fields = (app.meta or {}).get("form_fields", [])
    for field in form_fields:
        if field.get("required") and field["reference_key"] not in body.credentials:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field['display_name']}")

    try:
        handler = get_credential_handler(app_name)
        if not await handler.validate_credentials(body.credentials):
            raise HTTPException(status_code=400, detail="Credentials are invalid")
    except ValueError:
        pass

    integration = await create_integration(
        db, user_id=user_id, app_name=app_name,
        config=body.credentials,
        identifier=body.credentials.get("email") or body.credentials.get("username"),
    )

    return ConnectResponse(
        integration_id=integration.id, app_name=app_name,
        identifier=integration.identifier, status="active",
    )


# ── List / Get / Delete ──


@router.get("", response_model=list[IntegrationDTO])
async def list_integrations(db: DbDep, user_id: UserIdDep, _auth: TpsAuthDep):
    result = await db.exec(
        select(Integration).where(Integration.user_id == user_id, Integration.status == "active")
    )
    return [
        IntegrationDTO(id=i.id, app_name=i.app_name, identifier=i.identifier,
                        status=i.status, created_at=i.created_at.isoformat())
        for i in result.all()
    ]


@router.get("/{identifier}", response_model=IntegrationDTO)
async def get_integration(identifier: str, db: DbDep, user_id: UserIdDep, _auth: TpsAuthDep):
    stmt = select(Integration).where(
        Integration.user_id == user_id, Integration.app_name == identifier, Integration.status == "active",
    )
    result = await db.exec(stmt)
    integration = result.first()

    if not integration:
        stmt = select(Integration).where(
            Integration.id == identifier, Integration.user_id == user_id, Integration.status == "active",
        )
        result = await db.exec(stmt)
        integration = result.first()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    return IntegrationDTO(id=integration.id, app_name=integration.app_name,
                          identifier=integration.identifier, status=integration.status,
                          created_at=integration.created_at.isoformat())


@router.get("/{integration_id}/token")
async def get_token(integration_id: str, db: DbDep, user_id: UserIdDep, _auth: TpsAuthDep):
    """Return decrypted access token for an integration (used by Worker for authenticated API calls)."""
    from services.tps.integration_service import get_or_refresh
    try:
        config = await get_or_refresh(db, integration_id, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")
    # Check common token keys: access_token (OAuth), api_token (API key)
    access_token = config.get("access_token") or config.get("api_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token in integration config")
    return {"access_token": access_token}


@router.delete("/{integration_id}", response_model=OkResponse)
async def remove_integration(integration_id: str, db: DbDep, user_id: UserIdDep, _auth: TpsAuthDep):
    deleted = await delete_integration(db, integration_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")
    return OkResponse(ok=True)
