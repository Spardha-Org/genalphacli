"""Configuration and environment variable management."""

from __future__ import annotations

import os


def get_github_token() -> str | None:
    """Get GitHub token from environment."""
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
