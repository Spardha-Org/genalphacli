"""GitHub clone and framework detection activities."""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from temporalio import activity

from genalphacli.github import (
    cleanup_clone,
    clone_repo,
    detect_framework,
    fetch_repo_info,
    parse_github_url,
)
from worker.activities.schemas import CloneRepoInput, CloneRepoOutput

logger = logging.getLogger(__name__)


@activity.defn
def clone_repo_activity(input: CloneRepoInput) -> CloneRepoOutput:
    """Clone a GitHub repo and detect its framework.

    Uses the existing genalphacli clone infrastructure.
    Temp directory cleanup is handled by the workflow's finally block.
    """
    logger.info("Cloning %s/%s for service %s", input.owner, input.repo, input.service_id)

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
