"""Integration/App Store request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class InstallRequest(BaseModel):
    callback_path: str = "/app-store"
    form_data: dict | None = None


class ConnectRequest(BaseModel):
    credentials: dict[str, str]


class AppResponse(BaseModel):
    id: str
    app_code: int
    app_name: str
    display_name: str
    auth_type: str
    category: str
    provider: str
    meta: dict
    is_install_required: bool


class IntegrationResponse(BaseModel):
    id: str
    app_name: str
    identifier: str | None
    status: str
    created_at: str
