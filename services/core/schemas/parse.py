"""Parse request/response schemas."""

from __future__ import annotations

import re

from pydantic import BaseModel, field_validator

GITHUB_URL_RE = re.compile(
    r"^https://github\.com/([a-zA-Z0-9._-]+)/([a-zA-Z0-9._-]+?)(?:\.git)?/?$"
)
PYPI_PACKAGE_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$")


class ParseRequest(BaseModel):
    repo_url: str
    project_id: str

    @field_validator("repo_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        v = v.strip()
        if not GITHUB_URL_RE.match(v):
            raise ValueError("Invalid GitHub URL. Format: https://github.com/owner/repo")
        return v


class PyPIParseRequest(BaseModel):
    package_name: str
    project_id: str
    version: str | None = None

    @field_validator("package_name")
    @classmethod
    def validate_package_name(cls, v: str) -> str:
        v = v.strip()
        if not PYPI_PACKAGE_RE.match(v):
            raise ValueError("Invalid PyPI package name")
        return v


class ParseResponse(BaseModel):
    service_id: str
    workflow_id: str
    status: str
