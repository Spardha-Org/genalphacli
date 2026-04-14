"""Generate/Publish request/response schemas."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

CLI_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class GenerateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    service_id: str = Field(alias="serviceId")
    output_types: list[str] = Field(min_length=1, alias="outputTypes")
    cli_name: str = Field(alias="cliName")
    base_url: str = Field(alias="baseUrl")

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
    serviceId: str
    workflowId: str
    status: str
