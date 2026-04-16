"""GitHub repository connector: URL validation, metadata fetch, secure clone."""

from __future__ import annotations

import atexit
import logging
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

MAX_REPO_SIZE_KB = 500_000  # 500MB in KB
CACHE_DIR = Path.home() / ".cache" / "genalphacli"
GITHUB_URL_RE = re.compile(r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$")

# Track temp dirs for cleanup on unexpected exit
_temp_dirs: list[Path] = []


def _cleanup_temp_dirs() -> None:
    for d in _temp_dirs:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)


atexit.register(_cleanup_temp_dirs)


@dataclass
class RepoInfo:
    """Metadata about a GitHub repository."""

    owner: str
    repo: str
    full_name: str
    description: str
    default_branch: str
    size_kb: int
    languages: dict[str, int]
    clone_url: str


@dataclass
class ClonedRepo:
    """A cloned repository on disk."""

    path: Path
    info: RepoInfo
    detected_framework: str | None = None


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse a GitHub URL or owner/repo shorthand into (owner, repo).

    Accepts:
        https://github.com/owner/repo
        https://github.com/owner/repo.git
        owner/repo

    Rejects URLs with ports, userinfo, non-ASCII, fragments, query strings.
    """
    url = url.strip().rstrip("/")

    # Shorthand: owner/repo
    if GITHUB_URL_RE.match(url):
        owner, repo = url.split("/", 1)
        return owner, repo.removesuffix(".git")

    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise ValueError(f"Only HTTPS URLs are supported, got: {parsed.scheme or 'none'}")
    if parsed.netloc != "github.com":
        raise ValueError(f"Only github.com URLs are supported, got: {parsed.netloc}")
    if parsed.port:
        raise ValueError("URLs with ports are not supported")
    if "@" in (parsed.netloc or ""):
        raise ValueError("URLs with userinfo are not supported")
    if parsed.fragment or parsed.query:
        raise ValueError("URLs with fragments or query strings are not supported")

    # Path should be /owner/repo or /owner/repo.git
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL path: {parsed.path}")

    owner, repo = parts[0], parts[1]
    return owner, repo.removesuffix(".git")


def fetch_repo_info(owner: str, repo: str, token: str | None = None) -> RepoInfo:
    """Fetch repository metadata from the GitHub API."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Fetch repo metadata
    resp = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=headers,
        timeout=10,
    )
    if resp.status_code == 404:
        raise ValueError(f"Repository not found: {owner}/{repo}")
    if resp.status_code == 403:
        raise ValueError("GitHub API rate limit exceeded. Set GITHUB_TOKEN env var.")
    resp.raise_for_status()
    data = resp.json()

    # Check size
    size_kb = data.get("size", 0)
    if size_kb > MAX_REPO_SIZE_KB:
        raise ValueError(
            f"Repository too large: {size_kb / 1000:.0f}MB (max {MAX_REPO_SIZE_KB / 1000:.0f}MB)"
        )

    # Fetch languages
    lang_resp = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/languages",
        headers=headers,
        timeout=10,
    )
    languages = lang_resp.json() if lang_resp.ok else {}

    return RepoInfo(
        owner=owner,
        repo=repo,
        full_name=f"{owner}/{repo}",
        description=data.get("description", "") or "",
        default_branch=data.get("default_branch", "main"),
        size_kb=size_kb,
        languages=languages,
        clone_url=f"https://github.com/{owner}/{repo}.git",
    )


def clone_repo(info: RepoInfo, token: str | None = None) -> Path:
    """Clone a repository securely with hooks disabled.

    Uses --no-checkout to sanitize .gitattributes before checkout.
    """
    # Create temp dir with restricted permissions
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CACHE_DIR, 0o700)
    clone_dir = Path(tempfile.mkdtemp(dir=CACHE_DIR, prefix=f"{info.repo}-"))
    _temp_dirs.append(clone_dir)

    clone_url = info.clone_url
    if token:
        clone_url = f"https://x-access-token:{token}@github.com/{info.owner}/{info.repo}.git"

    # Step 1: Clone with --no-checkout to prevent hook/filter execution
    cmd = [
        "git",
        "clone",
        "--no-checkout",
        "--depth",
        "1",
        "--single-branch",
        "--config",
        "core.hooksPath=/dev/null",
        "--config",
        "core.fsmonitor=false",
        "--no-recurse-submodules",
        clone_url,
        str(clone_dir),
    ]

    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Git clone failed: {result.stderr.strip()}")

    # Step 2: Sanitize .gitattributes (remove filter= directives)
    gitattributes = clone_dir / ".gitattributes"
    if gitattributes.exists():
        content = gitattributes.read_text()
        # Remove lines with filter= directives
        sanitized = "\n".join(line for line in content.splitlines() if "filter=" not in line)
        gitattributes.write_text(sanitized)

    # Step 3: Checkout after sanitization
    checkout_result = subprocess.run(
        ["git", "-C", str(clone_dir), "checkout"],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )

    if checkout_result.returncode != 0:
        raise RuntimeError(f"Git checkout failed: {checkout_result.stderr.strip()}")

    return clone_dir


_DEP_FILES = [
    "requirements.txt",
    "requirements/base.txt",
    "requirements/main.txt",
    "pyproject.toml",
    "setup.py",
    "Pipfile",
    "setup.cfg",
]

_FRAMEWORK_KEYWORDS = {
    "fastapi": "fastapi",
    "djangorestframework": "django",
    "django-rest-framework": "django",
    "django": "django",
    # Phase 3+:
    # "flask": "flask",
}


def detect_framework(repo_path: Path) -> str | None:
    """Detect the API framework used in the repository.

    Scans root-level and common subdirectories (backend/, app/, src/, api/)
    for dependency files. Currently supports: fastapi.
    """
    # Search root and common nested project directories
    search_roots = [repo_path]
    for subdir in ("backend", "app", "src", "api", "server", "service"):
        candidate = repo_path / subdir
        if candidate.is_dir():
            search_roots.append(candidate)

    for search_root in search_roots:
        result = _detect_in_directory(search_root)
        if result:
            return result

    return None


def _detect_in_directory(directory: Path) -> str | None:
    """Check a single directory for framework dependency files."""
    for dep_file in _DEP_FILES:
        path = directory / dep_file
        if not path.exists() or path.is_symlink():
            continue
        try:
            content = path.read_text(errors="ignore").lower()
        except OSError:
            continue
        for keyword, framework in _FRAMEWORK_KEYWORDS.items():
            if keyword in content:
                return framework
    return None


def cleanup_clone(clone_dir: Path) -> None:
    """Remove a cloned repository from disk."""
    if clone_dir.exists():
        shutil.rmtree(clone_dir, ignore_errors=True)
    if clone_dir in _temp_dirs:
        _temp_dirs.remove(clone_dir)
