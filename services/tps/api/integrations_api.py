"""Integration API interface — generated from openapi/integrations.yaml.

Controllers implement this Protocol. Do not put business logic here.
"""

from __future__ import annotations

from typing import Protocol

from services.tps.deps import DbDep, TpsAuthDep, UserIdDep


class IntegrationsApi(Protocol):
    """Interface for integration lifecycle endpoints."""

    async def list_integrations(
        self, db: DbDep, workspace_id: UserIdDep, _auth: TpsAuthDep
    ) -> list[dict]:
        """GET /integrations — list all active integrations for a workspace."""
        ...

    async def install_app(
        self, app_name: str, db: DbDep, workspace_id: UserIdDep, _auth: TpsAuthDep, body: dict | None = None
    ) -> dict:
        """POST /integrations/{app_name}/install — start OAuth flow."""
        ...

    async def exchange_oauth_code(
        self, app_name: str, body: dict, db: DbDep, workspace_id: UserIdDep, _auth: TpsAuthDep
    ) -> dict:
        """POST /integrations/{app_name}/exchange — exchange code+state for token."""
        ...

    async def connect_app(
        self, app_name: str, body: dict, db: DbDep, workspace_id: UserIdDep, _auth: TpsAuthDep
    ) -> dict:
        """POST /integrations/{app_name}/connect — connect credential-based app."""
        ...

    async def get_integration(
        self, identifier: str, db: DbDep, workspace_id: UserIdDep, _auth: TpsAuthDep
    ) -> dict:
        """GET /integrations/{identifier} — get by integration_id or app_name."""
        ...

    async def remove_integration(
        self, integration_id: str, db: DbDep, workspace_id: UserIdDep, _auth: TpsAuthDep
    ) -> dict:
        """DELETE /integrations/{integration_id} — disconnect."""
        ...
