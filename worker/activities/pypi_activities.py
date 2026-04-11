"""PyPI fetch and extract activities."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from temporalio import activity

from genalphacli.github import detect_framework
from genalphacli.pypi import (
    download_sdist,
    extract_sdist_safe,
    fetch_package_info,
    find_sdist_url,
)
from worker.activities.schemas import FetchPyPISdistInput, FetchPyPISdistOutput

logger = logging.getLogger(__name__)


@activity.defn
def fetch_pypi_sdist_activity(input: FetchPyPISdistInput) -> FetchPyPISdistOutput:
    """Fetch a PyPI sdist, download, extract, and detect framework."""
    logger.info(
        "Fetching PyPI package %s (version=%s) for service %s",
        input.package_name,
        input.version or "latest",
        input.service_id,
    )

    info = fetch_package_info(input.package_name)
    sdist = find_sdist_url(info, version=input.version)

    if not sdist:
        version_msg = f" v{input.version}" if input.version else ""
        raise ValueError(
            f"No source distribution found for {input.package_name}{version_msg}. "
            "Only pre-built wheels may be available for this release."
        )

    download_dir = Path(tempfile.mkdtemp(prefix="pypi-"))
    tar_path = download_sdist(sdist.url, download_dir, sdist.sha256)
    extract_dir = extract_sdist_safe(tar_path, download_dir / "src")
    framework = detect_framework(extract_dir)

    logger.info(
        "Extracted %s v%s to %s, detected framework: %s",
        info.name,
        sdist.version,
        extract_dir,
        framework or "unknown",
    )

    return FetchPyPISdistOutput(
        extract_dir=str(extract_dir),
        framework=framework,
        package_version=sdist.version,
        package_summary=info.summary,
    )
