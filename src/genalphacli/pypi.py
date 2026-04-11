"""PyPI connector: fetch package metadata, download and extract source distributions."""

from __future__ import annotations

import hashlib
import logging
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

MAX_EXTRACT_SIZE_BYTES = 500_000_000  # 500MB
PYPI_BASE_URL = "https://pypi.org"
USER_AGENT = "genalphacli/1.0"


@dataclass
class PackageInfo:
    """Metadata about a PyPI package."""

    name: str
    version: str
    summary: str
    author: str | None
    license: str | None
    home_page: str | None
    releases: dict  # version -> list of file dicts


@dataclass
class SdistInfo:
    """Info about a specific source distribution file."""

    filename: str
    url: str
    sha256: str
    size: int
    version: str


def fetch_package_info(package_name: str) -> PackageInfo:
    """Fetch package metadata from the PyPI JSON API."""
    url = f"{PYPI_BASE_URL}/pypi/{package_name}/json"
    resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=30.0)

    if resp.status_code == 404:
        raise ValueError(f"Package not found on PyPI: {package_name}")
    resp.raise_for_status()

    data = resp.json()
    info = data["info"]

    return PackageInfo(
        name=info["name"],
        version=info["version"],
        summary=info.get("summary", "") or "",
        author=info.get("author"),
        license=info.get("license"),
        home_page=info.get("home_page"),
        releases=data.get("releases", {}),
    )


def _is_stable_version(version: str) -> bool:
    """Check if a version string looks like a stable release (not pre-release)."""
    pre_release_markers = ("a", "b", "rc", "dev", "alpha", "beta", "preview")
    v_lower = version.lower()
    return not any(marker in v_lower for marker in pre_release_markers)


def find_sdist_url(
    package_info: PackageInfo, version: str | None = None
) -> SdistInfo | None:
    """Find the sdist download URL for a package version.

    If version is None, uses the latest stable version.
    Skips yanked releases.
    """
    if version:
        # Specific version requested
        files = package_info.releases.get(version, [])
        for f in files:
            if f.get("packagetype") == "sdist" and not f.get("yanked"):
                return SdistInfo(
                    filename=f["filename"],
                    url=f["url"],
                    sha256=f["digests"]["sha256"],
                    size=f["size"],
                    version=version,
                )
        return None

    # Find latest stable version with an sdist
    # releases are not guaranteed to be ordered, so check the info.version first
    latest = package_info.version
    if latest and _is_stable_version(latest):
        result = find_sdist_url(package_info, latest)
        if result:
            return result

    # Fallback: iterate versions in reverse order (they're usually chronological)
    from packaging.version import Version, InvalidVersion

    versions = []
    for v in package_info.releases:
        try:
            parsed = Version(v)
            if not parsed.is_prerelease and not parsed.is_devrelease:
                versions.append((parsed, v))
        except InvalidVersion:
            continue

    for _, v_str in sorted(versions, reverse=True):
        result = find_sdist_url(package_info, v_str)
        if result:
            return result

    return None


def download_sdist(url: str, dest_dir: Path, expected_sha256: str) -> Path:
    """Download an sdist tarball and verify its SHA256 digest."""
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = url.rsplit("/", 1)[-1]
    tar_path = dest_dir / filename

    logger.info("Downloading sdist: %s", filename)

    with httpx.stream("GET", url, headers={"User-Agent": USER_AGENT}, timeout=120.0) as resp:
        resp.raise_for_status()
        sha256 = hashlib.sha256()
        with open(tar_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=65536):
                f.write(chunk)
                sha256.update(chunk)

    actual_hash = sha256.hexdigest()
    if actual_hash != expected_sha256:
        tar_path.unlink(missing_ok=True)
        raise ValueError(
            f"SHA256 mismatch for {filename}: expected {expected_sha256}, got {actual_hash}"
        )

    logger.info("Downloaded and verified: %s (%s bytes)", filename, tar_path.stat().st_size)
    return tar_path


def extract_sdist_safe(
    tar_path: Path,
    extract_dir: Path,
    max_size_bytes: int = MAX_EXTRACT_SIZE_BYTES,
) -> Path:
    """Safely extract a .tar.gz sdist with path traversal protection and size limits.

    Uses Python 3.12+ tarfile 'data' filter to block path traversal attacks.
    """
    extract_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=extract_dir, filter="data")

    # Verify extracted size
    total_size = sum(f.stat().st_size for f in extract_dir.rglob("*") if f.is_file())
    if total_size > max_size_bytes:
        shutil.rmtree(extract_dir, ignore_errors=True)
        raise ValueError(
            f"Extracted size {total_size / 1_000_000:.0f}MB exceeds "
            f"limit {max_size_bytes / 1_000_000:.0f}MB"
        )

    # Sdists have a single top-level directory (e.g., package-1.0.0/)
    subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
    if len(subdirs) == 1:
        return subdirs[0]
    return extract_dir
