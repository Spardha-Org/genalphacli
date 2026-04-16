"""Pipeline orchestrator: runs parsing layers, merges results, builds CommandGraph."""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path

from genalphacli.models import (
    AuthConfig,
    CommandGraph,
    CommandParam,
    HttpMethod,
    OutputConfig,
    ParsedRoute,
    ParseMetadata,
    ParseWarning,
    ResponseFormat,
    Subcommand,
)

logger = logging.getLogger(__name__)

IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
}


def index_files(repo_root: Path) -> dict[str, list[Path]]:
    """Single-pass file indexing using os.scandir, respecting ignore dirs.

    Returns a dict mapping file extensions to lists of file paths.
    """
    file_index: dict[str, list[Path]] = {}

    def _scan(directory: Path) -> None:
        try:
            entries = os.scandir(directory)
        except PermissionError:
            return

        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                if entry.name not in IGNORE_DIRS and not entry.name.startswith("."):
                    _scan(Path(entry.path))
            elif entry.is_file(follow_symlinks=False):
                ext = Path(entry.name).suffix.lower()
                if ext:
                    file_index.setdefault(ext, []).append(Path(entry.path))

    _scan(repo_root)
    return file_index


def normalize_path(path: str) -> str:
    """Normalize a path for route identity comparison.

    Converts path params to wildcards: /users/{id} -> /users/{}
    Strips trailing slashes.
    """
    normalized = re.sub(r"\{[^}]+\}", "{}", path)
    return normalized.rstrip("/") or "/"


def merge_routes(
    *route_lists: list[ParsedRoute],
) -> list[ParsedRoute]:
    """Merge routes from multiple layers. Later layers win on conflicts.

    Route identity is (http_method, normalized_path).
    """
    merged: dict[tuple[str, str], ParsedRoute] = {}

    for routes in route_lists:
        for route in routes:
            key = (route.method.value, normalize_path(route.path))
            if key in merged:
                existing = merged[key]
                logger.debug(
                    "Route conflict %s %s: layer %s overrides layer %s",
                    route.method.value,
                    route.path,
                    route.source_layer.name,
                    existing.source_layer.name,
                )
            merged[key] = route

    return list(merged.values())


def routes_to_command_graph(
    routes: list[ParsedRoute],
    command_name: str = "api",
    base_url: str = "",
    auth: AuthConfig | None = None,
    model_registry: dict[str, dict] | None = None,
    metadata: ParseMetadata | None = None,
) -> CommandGraph:
    """Convert parsed routes into a CommandGraph."""
    subcommands: list[Subcommand] = []

    for route in routes:
        # Generate command name from method + path
        cmd_name = _route_to_command_name(route)

        # Convert params
        cmd_params = [
            CommandParam(
                name=p.name,
                flag=f"--{p.name.replace('_', '-')}",
                type=p.param_type,
                required=p.required,
                description=p.description,
                default=p.default,
                enum_values=p.enum_values,
            )
            for p in route.params
        ]

        subcommands.append(
            Subcommand(
                name=cmd_name,
                description=route.description,
                method=route.method,
                endpoint=route.path,
                params=cmd_params,
                output=_build_output_config(route, model_registry or {}),
            )
        )

    return CommandGraph(
        command=command_name,
        base_url=base_url,
        auth=auth or AuthConfig(),
        subcommands=subcommands,
        metadata=metadata or ParseMetadata(),
    )


def _build_output_config(route: ParsedRoute, model_registry: dict[str, dict]) -> OutputConfig:
    """Build OutputConfig with resolved response model schema."""
    from genalphacli.parsers.model_extractor import resolve_response_model

    resolved = None
    if route.response_model:
        resolved = resolve_response_model(route.response_model, model_registry)

    # Use OpenAPI response_schema if we have it and no AST-resolved model
    schema = resolved or route.response_schema

    return OutputConfig(
        format=route.response_format,
        content_type=_format_to_content_type(route.response_format),
        response_model=route.response_model,
        response_schema=schema,
    )


def _format_to_content_type(fmt: ResponseFormat) -> str:
    """Map ResponseFormat to a standard content-type string."""
    return {
        ResponseFormat.JSON: "application/json",
        ResponseFormat.HTML: "text/html",
        ResponseFormat.TEXT: "text/plain",
        ResponseFormat.XML: "application/xml",
        ResponseFormat.BINARY: "application/octet-stream",
        ResponseFormat.FILE: "application/octet-stream",
        ResponseFormat.STREAM: "application/octet-stream",
    }.get(fmt, "application/json")


def _route_to_command_name(route: ParsedRoute) -> str:
    """Generate a CLI command name from a route.

    GET /users -> list-users
    GET /users/{id} -> get-user
    POST /users -> create-user
    DELETE /users/{id} -> delete-user
    """
    # Use function name if meaningful
    name = route.function_name
    if name and name not in ("root", "index", "handler"):
        return name.replace("_", "-")

    # Generate from method + path
    segments = [s for s in route.path.strip("/").split("/") if s and not s.startswith("{")]
    path_part = "-".join(segments) if segments else "root"

    method_prefix = {
        HttpMethod.GET: "get",
        HttpMethod.POST: "create",
        HttpMethod.PUT: "update",
        HttpMethod.PATCH: "patch",
        HttpMethod.DELETE: "delete",
    }
    prefix = method_prefix.get(route.method, route.method.value.lower())
    return f"{prefix}-{path_part}"


def run_pipeline(
    repo_root: Path,
    framework: str | None = None,
    command_name: str = "api",
    user_base_url: str | None = None,
    user_auth_type: str | None = None,
    user_auth_env_var: str | None = None,
) -> CommandGraph:
    """Run the full parsing pipeline on a cloned repository.

    Layer 1: OpenAPI spec parsing
    Layer 2: FastAPI AST parsing (if framework detected)
    Config detection: base_url and auth from .env files + code patterns
    Merge results, build CommandGraph.
    """
    start_time = time.monotonic()
    all_warnings: list[ParseWarning] = []

    # Index files
    file_index = index_files(repo_root)
    files_scanned = sum(len(f) for f in file_index.values())

    # Layer 1: OpenAPI
    from genalphacli.parsers.openapi_parser import parse_openapi

    openapi_routes, openapi_warnings = parse_openapi(repo_root)
    all_warnings.extend(openapi_warnings)
    logger.info("Layer 1 (OpenAPI): %d routes", len(openapi_routes))

    # Layer 2: FastAPI AST
    ast_routes: list[ParsedRoute] = []
    if framework == "fastapi" or framework is None:
        py_files = file_index.get(".py", [])
        if py_files:
            from genalphacli.parsers.fastapi_parser import parse_fastapi

            ast_routes, ast_warnings = parse_fastapi(repo_root, py_files)
            all_warnings.extend(ast_warnings)
            logger.info("Layer 2 (AST): %d routes", len(ast_routes))

    # Layer 2b: Django/DRF AST
    if framework == "django" or (framework is None and not ast_routes):
        py_files = file_index.get(".py", [])
        if py_files:
            from genalphacli.parsers.django_parser import parse_django

            django_routes, django_warnings = parse_django(repo_root, py_files)
            ast_routes.extend(django_routes)
            all_warnings.extend(django_warnings)
            logger.info("Layer 2b (Django AST): %d routes", len(django_routes))

    # Merge: later layer wins
    merged = merge_routes(openapi_routes, ast_routes)
    logger.info("Merged: %d routes", len(merged))

    # Build metadata
    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    layer_counts = {}
    for route in merged:
        layer_name = route.source_layer.name
        layer_counts[layer_name] = layer_counts.get(layer_name, 0) + 1

    metadata = ParseMetadata(
        warnings=all_warnings,
        total_routes=len(merged),
        layer_counts=layer_counts,
        files_scanned=files_scanned,
        parse_time_ms=elapsed_ms,
    )

    # Detect config (base_url, auth)
    from genalphacli.config_detector import detect_config, get_base_url, merge_config

    detected = detect_config(repo_root)
    base_url = get_base_url(detected, user_base_url)
    auth = merge_config(detected, user_base_url, user_auth_type, user_auth_env_var)

    if detected.detection_sources:
        for source in detected.detection_sources:
            all_warnings.append(ParseWarning(message=f"Config detected: {source}", severity="info"))

    # Rebuild metadata with any new warnings
    metadata = ParseMetadata(
        warnings=all_warnings,
        total_routes=len(merged),
        layer_counts=layer_counts,
        files_scanned=files_scanned,
        parse_time_ms=elapsed_ms,
    )

    # Extract Pydantic model schemas for response_model resolution
    from genalphacli.parsers.model_extractor import extract_models

    py_files = file_index.get(".py", [])
    model_registry = extract_models(py_files) if py_files else {}

    # Build command graph
    return routes_to_command_graph(
        merged,
        command_name=command_name,
        base_url=base_url,
        auth=auth,
        model_registry=model_registry,
        metadata=metadata,
    )
