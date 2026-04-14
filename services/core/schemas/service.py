"""Service request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class ServiceResponse(BaseModel):
    id: str
    project_id: str
    name: str
    repo_url: str | None
    source_type: str
    source_version: str | None = None
    framework: str | None
    status: str
    route_graph: dict | None = None
    error_message: str | None = None
    artifact_id: str | None = None
    metadata: dict | None = None
    created_at: str


class ServiceListItem(BaseModel):
    id: str
    project_id: str
    name: str
    repo_url: str | None
    framework: str | None
    status: str
    error_message: str | None = None
    created_at: str


class AuthConfigRequest(BaseModel):
    login_endpoint: str = ""
    login_params: list[str] = []
    refresh_endpoint: str = ""
    auth_type: str = "bearer"


class StatusUpdateRequest(BaseModel):
    """Called by the Temporal worker to update service status."""

    status: str
    error_message: str | None = None
    framework: str | None = None
    route_graph: dict | None = None
    metadata: dict | None = None
