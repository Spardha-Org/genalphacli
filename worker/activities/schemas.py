"""Dataclass schemas for Temporal activity inputs/outputs.

Use dataclasses (not Pydantic) for Temporal serialization compatibility.
All fields must be JSON-serializable — use str for file paths, dict for models.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CloneRepoInput:
    """Input for clone_repo_activity."""

    owner: str
    repo: str
    user_id: str
    service_id: str
    workspace_id: str = ""
    integration_id: str = ""  # If set, clone via TPS (authenticated)


@dataclass
class CloneRepoOutput:
    """Output from clone_repo_activity."""

    clone_dir: str
    framework: str | None


@dataclass
class ParseRoutesInput:
    """Input for parse_routes_activity."""

    clone_dir: str
    framework: str | None
    command_name: str


@dataclass
class ParseRoutesOutput:
    """Output from parse_routes_activity."""

    route_graph: dict  # CommandGraph.model_dump()
    route_count: int
    parse_time_ms: int
    warnings: list[str] = field(default_factory=list)


@dataclass
class GeneratePackagesInput:
    """Input for generate_packages_activity."""

    route_graph: dict  # CommandGraph as dict
    cli_name: str
    base_url: str
    output_types: list[str]  # ["cli", "mcp"]
    service_id: str


@dataclass
class GeneratePackagesOutput:
    """Output from generate_packages_activity."""

    output_dir: str


@dataclass
class PackageZipInput:
    """Input for package_zip_activity."""

    output_dir: str
    cli_name: str
    service_id: str


@dataclass
class PackageZipOutput:
    """Output from package_zip_activity."""

    zip_path: str
    zip_size_bytes: int


@dataclass
class UploadArtifactInput:
    """Input for upload_artifact_activity."""

    zip_path: str
    service_id: str
    artifact_type: str  # "cli" or "mcp"
    filename: str


@dataclass
class UploadArtifactOutput:
    """Output from upload_artifact_activity."""

    artifact_id: str
    file_size: int
