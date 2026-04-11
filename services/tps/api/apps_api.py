"""App Marketplace API interface — generated from openapi/apps.yaml.

Controllers implement this Protocol. Do not put business logic here.
"""

from __future__ import annotations

from typing import Protocol

from services.tps.deps import DbDep, TpsAuthDep


class AppsApi(Protocol):
    """Interface for app marketplace endpoints."""

    async def list_apps(
        self, db: DbDep, _auth: TpsAuthDep, category: int | None = None
    ) -> list[dict]:
        """GET /apps — list all active apps, optionally filtered by category."""
        ...

    async def get_app(
        self, identifier: str, db: DbDep, _auth: TpsAuthDep
    ) -> dict:
        """GET /apps/{identifier} — get app by app_name or app_code."""
        ...
