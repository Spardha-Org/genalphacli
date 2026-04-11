"""Test fixtures for TPS service tests.

Uses SQLite in-memory DB. Overrides TPS auth dependencies.
"""

from __future__ import annotations

import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import os

# Set test Fernet key before importing crypto module
from cryptography.fernet import Fernet
os.environ.setdefault("TPS_FERNET_KEYS", Fernet.generate_key().decode())

from services.tps.models import AppMarketplace, Integration, OAuthState
import services.tps.crypto as crypto_module
from services.tps.crypto import encrypt_config

# Reset the singleton so it picks up the test key
crypto_module._fernet = None


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


@pytest_asyncio.fixture
async def seed_data(db):
    """Seed a GitHub app and an active integration."""
    github_app = AppMarketplace(
        id="app-github",
        app_code=1,
        app_name="github",
        display_name="GitHub",
        auth_type="oauth2",
        category="source_control",
        provider="native",
        meta={
            "icon": "https://cdn.simpleicons.org/github/white",
            "description": "Connect your GitHub repositories",
        },
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        scopes="read:user user:email repo",
        is_install_required=True,
    )
    db.add(github_app)

    # Add a credential-based app for testing
    cloudflare_app = AppMarketplace(
        id="app-cloudflare",
        app_code=90,
        app_name="cloudflare",
        display_name="Cloudflare",
        auth_type="api_key",
        category="hosting",
        provider="native",
        meta={
            "icon": "https://cdn.simpleicons.org/cloudflare/F38020",
            "description": "Deploy to Cloudflare Workers",
            "form_fields": [
                {
                    "reference_key": "api_token",
                    "type": "password",
                    "display_name": "API Token",
                    "required": True,
                    "placeholder": "Bearer token from Cloudflare dashboard",
                },
            ],
        },
        is_install_required=False,
    )
    db.add(cloudflare_app)

    # A coming_soon app
    railway_app = AppMarketplace(
        id="app-railway",
        app_code=91,
        app_name="railway",
        display_name="Railway",
        auth_type="oauth2",
        category="coming_soon",
        provider="native",
        meta={"icon": "https://cdn.simpleicons.org/railway/white"},
        is_install_required=True,
        active=False,
    )
    db.add(railway_app)

    await db.commit()

    return {
        "github_app": github_app,
        "cloudflare_app": cloudflare_app,
        "railway_app": railway_app,
    }


@pytest_asyncio.fixture
async def client(engine, seed_data):
    """Create an async test client with dependency overrides."""
    from services.tps.main import app
    from services.tps.deps import get_db, validate_tps_secret, get_workspace_id

    async def override_get_db():
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    async def override_validate_tps_secret():
        return None

    async def override_get_workspace_id():
        return "test-ws"

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[validate_tps_secret] = override_validate_tps_secret
    app.dependency_overrides[get_workspace_id] = override_get_workspace_id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
