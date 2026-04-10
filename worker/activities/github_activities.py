"""GitHub clone and framework detection activities."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

import httpx
from temporalio import activity

from genalphacli.github import (
    clone_repo,
    detect_framework,
    fetch_repo_info,
)
from worker.activities.schemas import CloneRepoInput, CloneRepoOutput

logger = logging.getLogger(__name__)

CORE_URL = os.environ.get("CORE_URL", "http://localhost:8000")
TPS_URL = os.environ.get("TPS_URL", "http://localhost:8001")
TPS_SECRET = os.environ.get("TPS_SECRET", "dev-tps-shared-secret")


@activity.defn
def clone_repo_activity(input: CloneRepoInput) -> CloneRepoOutput:
    """Clone a GitHub repo and detect its framework.

    If integration_id is provided, clones via TPS (authenticated — for private repos).
    Otherwise, clones directly (public repos only).
    """
    logger.info("Cloning %s/%s for service %s", input.owner, input.repo, input.service_id)

    if input.integration_id:
        # Clone via TPS — uses the stored encrypted GitHub token
        logger.info("Using TPS integration %s for authenticated clone", input.integration_id)
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{TPS_URL}/integrations/{input.integration_id}/clone",
                json={"repo_url": f"https://github.com/{input.owner}/{input.repo}"},
                headers={
                    "X-TPS-Secret": TPS_SECRET,
                    "X-Workspace-ID": input.workspace_id,
                },
            )
            response.raise_for_status()
            data = response.json()
            clone_dir = Path(data["clone_dir"])
    else:
        # Direct clone — public repos only
        logger.info("No integration — cloning public repo directly")
        info = fetch_repo_info(input.owner, input.repo, token=None)
        clone_dir = clone_repo(info, token=None)

    framework = detect_framework(clone_dir)

    logger.info(
        "Cloned to %s, detected framework: %s",
        clone_dir,
        framework or "unknown",
    )

    return CloneRepoOutput(
        clone_dir=str(clone_dir),
        framework=framework,
    )


@activity.defn
def cleanup_clone_activity(clone_dir: str) -> None:
    """Clean up a cloned repo directory."""
    path = Path(clone_dir)
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
        logger.info("Cleaned up clone directory: %s", clone_dir)
