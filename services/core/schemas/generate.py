"""Generate/Publish request/response schemas."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

CLI_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class GenerateRequest(BaseModel):
    service_id: str
    output_types: list[str] = Field(min_length=1)
    cli_name: str
    base_url: str

    @field_validator("cli_name")
    @classmethod
    def validate_cli_name(cls, v: str) -> str:
        if not CLI_NAME_RE.match(v):
            raise ValueError("CLI name must be lowercase alphanumeric with underscores")
        return v

    @field_validator("output_types")
    @classmethod
    def validate_output_types(cls, v: list[str]) -> list[str]:
        allowed = {"cli", "mcp"}
        invalid = set(v) - allowed
        if invalid:
            raise ValueError(f"Invalid output types: {invalid}. Allowed: {allowed}")
        return v


class PublishRequest(GenerateRequest):
    """Same fields as GenerateRequest — publish generates then uploads."""

    pass


class GenerateResponse(BaseModel):
    service_id: str
    workflow_id: str
    status: str
