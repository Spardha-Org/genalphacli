"""Tests for TPS architecture rewrite — marketplace, multi-auth, integration lifecycle."""

from __future__ import annotations

import time

import pytest
from services.tps.crypto import encrypt_config, decrypt_config

pytestmark = pytest.mark.asyncio


class TestAppMarketplace:
    """GET /apps"""

    async def test_list_apps_returns_active_only(self, client, seed_data):
        resp = await client.get("/apps")
        assert resp.status_code == 200
        apps = resp.json()
        names = [a["app_name"] for a in apps]
        assert "github" in names
        assert "cloudflare" in names
        assert "railway" not in names  # inactive

    async def test_app_response_includes_meta(self, client, seed_data):
        resp = await client.get("/apps")
        apps = resp.json()
        github = next(a for a in apps if a["app_name"] == "github")
        assert "meta" in github
        assert github["meta"]["icon"] == "https://cdn.simpleicons.org/github/white"

    async def test_app_response_includes_category(self, client, seed_data):
        resp = await client.get("/apps")
        apps = resp.json()
        github = next(a for a in apps if a["app_name"] == "github")
        cloudflare = next(a for a in apps if a["app_name"] == "cloudflare")
        assert github["category"] == "source_control"
        assert cloudflare["category"] == "hosting"

    async def test_app_response_includes_auth_type(self, client, seed_data):
        resp = await client.get("/apps")
        apps = resp.json()
        github = next(a for a in apps if a["app_name"] == "github")
        cloudflare = next(a for a in apps if a["app_name"] == "cloudflare")
        assert github["auth_type"] == "oauth2"
        assert cloudflare["auth_type"] == "api_key"

    async def test_cloudflare_has_form_fields(self, client, seed_data):
        resp = await client.get("/apps")
        apps = resp.json()
        cloudflare = next(a for a in apps if a["app_name"] == "cloudflare")
        fields = cloudflare["meta"].get("form_fields", [])
        assert len(fields) == 1
        assert fields[0]["reference_key"] == "api_token"
        assert fields[0]["required"] is True


class TestOAuthInstallFlow:
    """POST /integrations/{app_name}/install — TPS is stateless"""

    async def test_install_nonexistent_app(self, client):
        resp = await client.post(
            "/integrations/nonexistent/install",
            json={"state": "test-state", "redirect_uri": "http://localhost/callback"},
        )
        assert resp.status_code == 404

    async def test_install_credential_app_rejects(self, client, seed_data):
        resp = await client.post(
            "/integrations/cloudflare/install",
            json={"state": "test-state", "redirect_uri": "http://localhost/callback"},
        )
        assert resp.status_code == 400
        assert "credential flow" in resp.json()["detail"]

    async def test_install_github_returns_authorize_url(self, client, seed_data):
        resp = await client.post(
            "/integrations/github/install",
            json={"state": "my-encrypted-state", "redirect_uri": "http://localhost/callback"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "authorize_url" in data
        assert "github.com/login/oauth/authorize" in data["authorize_url"]
        assert "my-encrypted-state" in data["authorize_url"]


class TestCredentialConnectFlow:
    """POST /integrations/{app_name}/connect"""

    async def test_connect_nonexistent_app(self, client):
        resp = await client.post(
            "/integrations/nonexistent/connect",
            json={"credentials": {"api_token": "test"}},
        )
        assert resp.status_code == 404

    async def test_connect_oauth_app_rejects(self, client, seed_data):
        """GitHub is OAuth — connect should reject it."""
        resp = await client.post(
            "/integrations/github/connect",
            json={"credentials": {"api_token": "test"}},
        )
        assert resp.status_code == 400
        assert "OAuth flow" in resp.json()["detail"]

    async def test_connect_cloudflare_missing_required_field(self, client, seed_data):
        resp = await client.post(
            "/integrations/cloudflare/connect",
            json={"credentials": {}},
        )
        assert resp.status_code == 400
        assert "API Token" in resp.json()["detail"]

    async def test_connect_cloudflare_success(self, client, seed_data):
        resp = await client.post(
            "/integrations/cloudflare/connect",
            json={"credentials": {"api_token": "cf_test_token_123"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["app_name"] == "cloudflare"
        assert data["status"] == "active"
        assert "integration_id" in data

    async def test_connect_appears_in_list(self, client, seed_data):
        await client.post(
            "/integrations/cloudflare/connect",
            json={"credentials": {"api_token": "cf_token"}},
        )
        resp = await client.get("/integrations")
        assert resp.status_code == 200
        integrations = resp.json()
        assert any(i["app_name"] == "cloudflare" for i in integrations)


class TestListIntegrations:
    """GET /integrations"""

    async def test_list_empty(self, client, seed_data):
        resp = await client.get("/integrations")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_after_connect(self, client, seed_data):
        await client.post(
            "/integrations/cloudflare/connect",
            json={"credentials": {"api_token": "cf_token"}},
        )
        resp = await client.get("/integrations")
        integrations = resp.json()
        assert len(integrations) == 1
        assert integrations[0]["app_name"] == "cloudflare"
        assert "identifier" in integrations[0]
        assert "created_at" in integrations[0]


class TestDeleteIntegration:
    """DELETE /integrations/{integration_id}"""

    async def test_delete_nonexistent(self, client):
        resp = await client.delete("/integrations/nonexistent")
        assert resp.status_code == 404

    async def test_delete_integration(self, client, seed_data):
        # Connect first
        connect_resp = await client.post(
            "/integrations/cloudflare/connect",
            json={"credentials": {"api_token": "cf_token"}},
        )
        integration_id = connect_resp.json()["integration_id"]

        # Delete
        resp = await client.delete(f"/integrations/{integration_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Verify gone from list
        list_resp = await client.get("/integrations")
        assert len(list_resp.json()) == 0

    async def test_reconnect_after_delete(self, client, seed_data):
        """Reconnecting after disconnect should upsert."""
        # Connect
        connect_resp = await client.post(
            "/integrations/cloudflare/connect",
            json={"credentials": {"api_token": "old_token"}},
        )
        integration_id = connect_resp.json()["integration_id"]

        # Delete
        await client.delete(f"/integrations/{integration_id}")

        # Reconnect
        reconnect_resp = await client.post(
            "/integrations/cloudflare/connect",
            json={"credentials": {"api_token": "new_token"}},
        )
        assert reconnect_resp.status_code == 200
        assert reconnect_resp.json()["status"] == "active"


class TestMultiFernet:
    """Encryption key rotation support."""

    def test_encrypt_decrypt_roundtrip(self):
        config = {"access_token": "ghp_test123", "token_type": "bearer"}
        encrypted = encrypt_config(config)
        decrypted = decrypt_config(encrypted)
        assert decrypted == config

    def test_encrypted_is_not_plaintext(self):
        config = {"access_token": "ghp_test123"}
        encrypted = encrypt_config(config)
        assert "ghp_test123" not in encrypted


class TestHealthEndpoint:
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "tps"
