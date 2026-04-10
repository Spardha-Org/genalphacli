"""Package generation activities — wraps existing CLI/MCP generators."""

from __future__ import annotations

import io
import logging
import os
import tempfile
import zipfile
from pathlib import Path

from temporalio import activity

from genalphacli.generators.mcp_generator import generate as gen_mcp
from genalphacli.generators.pip_generator import generate as gen_cli
from genalphacli.models import AuthConfig, BuildConfig, CommandGraph
import httpx

from worker.activities.schemas import (
    GeneratePackagesInput,
    GeneratePackagesOutput,
    PackageZipInput,
    PackageZipOutput,
    UploadArtifactInput,
    UploadArtifactOutput,
)

CORE_URL = os.environ.get("CORE_URL", "http://localhost:8000")

logger = logging.getLogger(__name__)


@activity.defn
def generate_packages_activity(input: GeneratePackagesInput) -> GeneratePackagesOutput:
    """Generate CLI and/or MCP packages from a CommandGraph.

    Reconstructs CommandGraph from dict, calls existing generators,
    and writes output to a temp directory.
    """
    graph = CommandGraph.model_validate(input.route_graph)

    config = BuildConfig(
        cli_name=input.cli_name,
        base_url=input.base_url,
        auth=AuthConfig(
            type=graph.auth.type if graph.auth else "none",
            env_var=graph.auth.env_var if graph.auth else None,
        ),
    )

    output_dir = Path(tempfile.mkdtemp(prefix=f"genalpha-gen-{input.service_id}-"))

    if "cli" in input.output_types:
        cli_path = gen_cli(graph, config, output_dir)
        logger.info("Generated CLI package at %s", cli_path)

    if "mcp" in input.output_types:
        mcp_path = gen_mcp(graph, config, output_dir)
        logger.info("Generated MCP package at %s", mcp_path)

    return GeneratePackagesOutput(output_dir=str(output_dir))


@activity.defn
def package_zip_activity(input: PackageZipInput) -> PackageZipOutput:
    """Package generated output directory into a downloadable zip."""
    output_dir = Path(input.output_dir)
    zip_dir = Path(tempfile.mkdtemp(prefix="genalpha-zip-"))
    zip_path = zip_dir / f"{input.cli_name}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(output_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(output_dir)
                zf.write(file_path, arcname)

    zip_size = zip_path.stat().st_size
    logger.info("Packaged zip at %s (%d bytes)", zip_path, zip_size)

    return PackageZipOutput(
        zip_path=str(zip_path),
        zip_size_bytes=zip_size,
    )


@activity.defn
def upload_artifact_activity(input: UploadArtifactInput) -> UploadArtifactOutput:
    """Read ZIP from disk and upload to Core as multipart/form-data."""
    zip_bytes = Path(input.zip_path).read_bytes()

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{CORE_URL}/services/{input.service_id}/artifacts",
            files={"file": (input.filename, zip_bytes, "application/zip")},
            data={"artifact_type": input.artifact_type},
        )
        response.raise_for_status()

    result = response.json()
    logger.info("Uploaded artifact %s for service %s (%d bytes)", result["artifact_id"], input.service_id, result["file_size"])

    return UploadArtifactOutput(
        artifact_id=result["artifact_id"],
        file_size=result["file_size"],
    )
