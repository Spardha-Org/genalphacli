"""Auto-detect base_url and auth configuration from repository signals.

Uses a layered approach:
1. Scan .env / .env.example files for URL and auth patterns
2. Parse source code for auth library usage (HTTPBearer, OAuth2, api_key)
3. Accept CLI overrides from the user (highest priority)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from genalphacli.models import AuthConfig, AuthType

# ── Patterns for .env file scanning ────────────────────────────

# URL patterns in env files
_URL_PATTERNS = [
    re.compile(r"^(?:BASE_URL|API_URL|SERVER_URL|APP_URL|BACKEND_URL)\s*=\s*(.+)", re.IGNORECASE),
    re.compile(r"^(?:HOST|HOSTNAME|DOMAIN)\s*=\s*(.+)", re.IGNORECASE),
]

# Port pattern
_PORT_PATTERN = re.compile(r"^(?:PORT|APP_PORT|SERVER_PORT)\s*=\s*(\d+)", re.IGNORECASE)

# Auth-related env var patterns
_AUTH_ENV_PATTERNS = {
    AuthType.BEARER: re.compile(
        r"^(JWT_SECRET|JWT_KEY|ACCESS_TOKEN|AUTH_SECRET|SECRET_KEY|TOKEN_SECRET)",
        re.IGNORECASE,
    ),
    AuthType.API_KEY: re.compile(
        r"^(API_KEY|X_API_KEY|SERVICE_KEY|APP_KEY)",
        re.IGNORECASE,
    ),
}

# Code-level auth patterns
_CODE_AUTH_PATTERNS = {
    AuthType.BEARER: [
        "HTTPBearer",
        "OAuth2PasswordBearer",
        "OAuth2PasswordRequestForm",
        "jwt.encode",
        "jwt.decode",
        "JWTBearer",
        "Bearer",
        "HTTPAuthorizationCredentials",
    ],
    AuthType.API_KEY: [
        "APIKeyHeader",
        "APIKeyCookie",
        "APIKeyQuery",
        "api_key",
        "x-api-key",
        "X-API-Key",
    ],
}

# Common env files to scan (in priority order)
_ENV_FILES = [
    ".env.example",
    ".env.sample",
    ".env.template",
    ".env.local",
    ".env.development",
    ".env",
]

# Subdirectories to search for env files
_SEARCH_DIRS = ["", "server", "backend", "app", "api", "src"]


@dataclass
class DetectedConfig:
    """Configuration signals detected from the repository."""

    base_url: str = ""
    port: str = ""
    auth_type: AuthType = AuthType.NONE
    auth_env_var: str = ""
    auth_env_vars_found: list[str] = field(default_factory=list)
    detection_sources: list[str] = field(default_factory=list)


def detect_config(repo_path: Path) -> DetectedConfig:
    """Detect base_url and auth configuration from repository signals."""
    config = DetectedConfig()

    # Layer 1: Scan .env files
    _scan_env_files(repo_path, config)

    # Layer 2: Parse code for auth patterns
    _scan_code_auth(repo_path, config)

    # Build base_url from detected signals
    if not config.base_url and config.port:
        config.base_url = f"http://localhost:{config.port}"

    return config


def _scan_env_files(repo_path: Path, config: DetectedConfig) -> None:
    """Scan .env files for URL and auth patterns."""
    for search_dir in _SEARCH_DIRS:
        dir_path = repo_path / search_dir if search_dir else repo_path
        if not dir_path.is_dir():
            continue

        for env_file in _ENV_FILES:
            env_path = dir_path / env_file
            if not env_path.is_file() or env_path.is_symlink():
                continue

            try:
                content = env_path.read_text(errors="ignore")
            except OSError:
                continue

            source_label = str(env_path.relative_to(repo_path))

            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Check for URL patterns
                if not config.base_url:
                    for pattern in _URL_PATTERNS:
                        match = pattern.match(line)
                        if match:
                            url = match.group(1).strip().strip("\"'")
                            if url.startswith("http"):
                                config.base_url = url
                                config.detection_sources.append(f"base_url from {source_label}")

                # Check for port
                if not config.port:
                    match = _PORT_PATTERN.match(line)
                    if match:
                        config.port = match.group(1)
                        config.detection_sources.append(f"port from {source_label}")

                # Check for auth env vars
                for auth_type, pattern in _AUTH_ENV_PATTERNS.items():
                    # Extract the var name (before =)
                    var_name = line.split("=")[0].strip()
                    if pattern.match(var_name):
                        config.auth_env_vars_found.append(var_name)
                        if config.auth_type == AuthType.NONE:
                            config.auth_type = auth_type
                            config.auth_env_var = var_name
                            config.detection_sources.append(
                                f"auth ({auth_type.value}) from {source_label}: {var_name}"
                            )


def _scan_code_auth(repo_path: Path, config: DetectedConfig) -> None:
    """Scan Python source files for auth library usage patterns."""
    py_files = [
        p
        for p in repo_path.rglob("*.py")
        if not p.is_symlink()
        and ".venv" not in p.parts
        and "__pycache__" not in p.parts
        and "node_modules" not in p.parts
        and "migrations" not in p.parts
    ]

    for py_file in py_files:
        try:
            content = py_file.read_text(errors="ignore")
        except OSError:
            continue

        source_label = str(py_file.relative_to(repo_path))

        for auth_type, patterns in _CODE_AUTH_PATTERNS.items():
            for pattern in patterns:
                if pattern in content:
                    if config.auth_type == AuthType.NONE:
                        config.auth_type = auth_type
                        msg = f"auth ({auth_type.value}) from code: {source_label}"
                        config.detection_sources.append(msg)
                    return  # First match is enough


def merge_config(
    detected: DetectedConfig,
    user_base_url: str | None = None,
    user_auth_type: str | None = None,
    user_auth_env_var: str | None = None,
) -> AuthConfig:
    """Merge detected config with user overrides. User input wins."""
    # Auth type: user override > detected
    auth_type = AuthType.NONE
    if user_auth_type:
        try:
            auth_type = AuthType(user_auth_type)
        except ValueError:
            auth_type = detected.auth_type
    else:
        auth_type = detected.auth_type

    # Auth env var: user override > detected
    auth_env_var = user_auth_env_var or detected.auth_env_var

    return AuthConfig(type=auth_type, env_var=auth_env_var)


def get_base_url(detected: DetectedConfig, user_base_url: str | None = None) -> str:
    """Get base URL with user override taking priority."""
    return user_base_url or detected.base_url
