"""Parse request/response schemas."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

GITHUB_URL_RE = re.compile(
    r"^https://github\.com/([a-zA-Z0-9._-]+)/([a-zA-Z0-9._-]+?)(?:\.git)?/?$"
)
PYPI_PACKAGE_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$")


class ParseRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    repo_url: str = Field(alias="repoUrl")
    project_id: str = Field(alias="projectId")

    @field_validator("repo_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        v = v.strip()
        if not GITHUB_URL_RE.match(v):
            raise ValueError("Invalid GitHub URL. Format: https://github.com/owner/repo")
        return v


class PyPIParseRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    package_name: str = Field(alias="packageName")
    project_id: str = Field(alias="projectId")
    version: str | None = None

    @field_validator("package_name")
    @classmethod
    def validate_package_name(cls, v: str) -> str:
        v = v.strip()
        if not PYPI_PACKAGE_RE.match(v):
            raise ValueError("Invalid PyPI package name")
        return v


class ParseResponse(BaseModel):
    serviceId: str
    workflowId: str
    status: str
