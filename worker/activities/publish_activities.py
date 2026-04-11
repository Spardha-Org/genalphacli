"""Publish generated packages to PyPI."""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
from pathlib import Path

import httpx
from temporalio import activity

from worker.activities.schemas import PublishToPyPIInput, PublishToPyPIOutput

logger = logging.getLogger(__name__)

TPS_URL = os.environ.get("TPS_URL", "http://localhost:8001")
TPS_SECRET = os.environ.get("TPS_SECRET", "dev-tps-shared-secret")

PYPI_UPLOAD_URL = "https://upload.pypi.org/legacy/"


def _fetch_pypi_token(integration_id: str, user_id: str) -> str:
    """Fetch the PyPI API token from TPS."""
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            f"{TPS_URL}/integrations/{integration_id}/token",
            headers={
                "X-TPS-Secret": TPS_SECRET,
                "X-User-ID": user_id,
            },
        )
        resp.raise_for_status()
    return resp.json()["access_token"]


def _build_package(package_dir: Path) -> list[Path]:
    """Build sdist and wheel using `python -m build`."""
    result = subprocess.run(
        ["python", "-m", "build", str(package_dir)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Build failed: {result.stderr}")

    dist_dir = package_dir / "dist"
    dist_files = list(dist_dir.glob("*"))
    if not dist_files:
        raise RuntimeError(f"No distribution files found in {dist_dir}")

    logger.info("Built %d distribution files: %s", len(dist_files), [f.name for f in dist_files])
    return dist_files


def _extract_metadata(package_dir: Path) -> tuple[str, str]:
    """Read package name and version from pyproject.toml."""
    pyproject = package_dir / "pyproject.toml"
    name, version = "", ""
    for line in pyproject.read_text().splitlines():
        line = line.strip()
        if line.startswith("name = "):
            name = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("version = "):
            version = line.split("=", 1)[1].strip().strip('"')
    if not name or not version:
        raise ValueError(f"Could not extract name/version from {pyproject}")
    return name, version


def _upload_to_pypi(token: str, dist_file: Path, name: str, version: str) -> None:
    """Upload a single distribution file to PyPI via the legacy upload API."""
    file_bytes = dist_file.read_bytes()
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    md5 = hashlib.md5(file_bytes).hexdigest()

    # Determine filetype and pyversion
    if dist_file.suffix == ".whl":
        filetype = "bdist_wheel"
        # Extract pyversion from wheel filename: name-ver-pyver-abi-platform.whl
        parts = dist_file.stem.split("-")
        pyversion = parts[2] if len(parts) >= 3 else "py3"
    elif dist_file.name.endswith(".tar.gz"):
        filetype = "sdist"
        pyversion = "source"
    else:
        filetype = "sdist"
        pyversion = "source"

    logger.info("Uploading %s to PyPI (%d bytes, type=%s, pyversion=%s)", dist_file.name, len(file_bytes), filetype, pyversion)

    form_data = {
        ":action": "file_upload",
        "protocol_version": "1",
        "name": name,
        "version": version,
        "filetype": filetype,
        "pyversion": pyversion,
        "md5_digest": md5,
        "sha256_digest": sha256,
        "metadata_version": "2.1",
    }

    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            PYPI_UPLOAD_URL,
            auth=("__token__", token),
            data=form_data,
            files={
                "content": (dist_file.name, file_bytes, "application/octet-stream"),
            },
        )

    if resp.status_code == 200:
        logger.info("Successfully uploaded %s", dist_file.name)
    elif resp.status_code == 409:
        logger.warning("File already exists on PyPI: %s (skipping)", dist_file.name)
    else:
        raise RuntimeError(
            f"PyPI upload failed ({resp.status_code}): {resp.text[:500]}"
        )


@activity.defn
def publish_to_pypi_activity(input: PublishToPyPIInput) -> PublishToPyPIOutput:
    """Build and publish a generated package to PyPI.

    Steps:
    1. Fetch PyPI API token from TPS
    2. Find the package directory (cli or mcp)
    3. Build sdist + wheel with `python -m build`
    4. Upload each dist file to PyPI
    """
    logger.info("Publishing %s package for service %s", input.package_type, input.service_id)

    # Fetch token
    token = _fetch_pypi_token(input.integration_id, input.user_id)

    # Find the package directory within the output dir
    output_dir = Path(input.output_dir)
    package_dirs = [d for d in output_dir.iterdir() if d.is_dir() and (d / "pyproject.toml").exists()]

    if not package_dirs:
        raise ValueError(f"No package with pyproject.toml found in {output_dir}")

    # If multiple packages (cli + mcp), pick the right one
    if len(package_dirs) > 1:
        suffix = "_mcp" if input.package_type == "mcp" else ""
        package_dirs = [d for d in package_dirs if d.name.endswith(suffix) == bool(suffix)]

    package_dir = package_dirs[0]
    name, version = _extract_metadata(package_dir)
    logger.info("Building package: %s v%s from %s", name, version, package_dir)

    # Build
    dist_files = _build_package(package_dir)

    # Upload each dist file
    for dist_file in dist_files:
        _upload_to_pypi(token, dist_file, name, version)

    published_url = f"https://pypi.org/project/{name}/{version}/"
    logger.info("Published to %s", published_url)

    return PublishToPyPIOutput(
        package_name=name,
        version=version,
        published_url=published_url,
    )
