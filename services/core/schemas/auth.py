"""Auth request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkResponse(BaseModel):
    message: str = "If that email exists, a login link was sent."


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None
    email_verified: bool


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str
    integration_id: str | None


class VerifyResponse(BaseModel):
    message: str
    user: UserResponse
    is_new_user: bool


class SessionResponse(BaseModel):
    user: UserResponse
    workspace: WorkspaceResponse | None
