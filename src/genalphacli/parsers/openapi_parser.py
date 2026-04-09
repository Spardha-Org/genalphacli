"""Layer 1: OpenAPI/Swagger spec parser.

Scans for spec files, parses with prance (local $ref only), and extracts routes.
"""

from __future__ import annotations

import logging
from pathlib import Path

from genalphacli.models import (
    CONTENT_TYPE_MAP,
    HttpMethod,
    ParamLocation,
    ParamType,
    ParsedRoute,
    ParseWarning,
    ResponseFormat,
    RouteParam,
    SourceLayer,
)

logger = logging.getLogger(__name__)

SPEC_FILENAMES = [
    "openapi.json",
    "openapi.yaml",
    "openapi.yml",
    "swagger.json",
    "swagger.yaml",
    "swagger.yml",
]

SPEC_DIRS = ["", "docs", "api-docs", "specs", "api", "doc"]

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def find_spec_files(repo_root: Path) -> list[Path]:
    """Scan for OpenAPI/Swagger spec files in common locations."""
    found = []
    for dir_name in SPEC_DIRS:
        search_dir = repo_root / dir_name if dir_name else repo_root
        if not search_dir.is_dir():
            continue
        for filename in SPEC_FILENAMES:
            spec_path = search_dir / filename
            if spec_path.is_file() and not spec_path.is_symlink():
                found.append(spec_path)
    return found


def parse_spec_file(spec_path: Path) -> tuple[list[ParsedRoute], list[ParseWarning]]:
    """Parse a single OpenAPI/Swagger spec file into routes."""
    from prance import BaseParser, ResolvingParser
    from prance.util.resolver import RESOLVE_INTERNAL

    routes: list[ParsedRoute] = []
    warnings: list[ParseWarning] = []

    # Try resolving internal $ref only (block remote URLs for security)
    try:
        parser = ResolvingParser(
            str(spec_path),
            resolve_types=RESOLVE_INTERNAL,
            strict=False,
            backend="openapi-spec-validator",
        )
        spec = parser.specification
    except Exception as e:
        # Fallback to unresolved spec
        warnings.append(
            ParseWarning(
                message=f"Full resolution failed, using raw spec: {e}",
                source_file=str(spec_path),
                layer=SourceLayer.OPENAPI,
            )
        )
        try:
            parser = BaseParser(str(spec_path), strict=False)
            spec = parser.specification
        except Exception as e2:
            warnings.append(
                ParseWarning(
                    message=f"Failed to parse spec: {e2}",
                    source_file=str(spec_path),
                    layer=SourceLayer.OPENAPI,
                    severity="error",
                )
            )
            return routes, warnings

    # Walk paths to extract routes
    paths = spec.get("paths", {})
    for path_str, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method_str, operation in path_item.items():
            if method_str not in HTTP_METHODS or not isinstance(operation, dict):
                continue

            params = _extract_params(operation, path_item)
            description = operation.get("summary", "") or operation.get("description", "")
            operation_id = operation.get("operationId", "")

            # Detect response format and schema from responses
            resp_format, resp_model, resp_schema = _extract_response_info(operation)

            try:
                route = ParsedRoute(
                    method=HttpMethod(method_str.upper()),
                    path=path_str,
                    function_name=operation_id or _path_to_name(method_str, path_str),
                    description=description,
                    params=params,
                    response_format=resp_format,
                    response_model=resp_model,
                    response_schema=resp_schema,
                    source_file=spec_path,
                    source_layer=SourceLayer.OPENAPI,
                    confidence=1.0,
                )
                routes.append(route)
            except Exception as e:
                warnings.append(
                    ParseWarning(
                        message=f"Failed to parse {method_str.upper()} {path_str}: {e}",
                        source_file=str(spec_path),
                        layer=SourceLayer.OPENAPI,
                    )
                )

    return routes, warnings


def _extract_params(operation: dict, path_item: dict) -> list[RouteParam]:
    """Extract parameters from an OpenAPI operation."""
    params: list[RouteParam] = []

    # Merge path-level and operation-level parameters
    all_params = path_item.get("parameters", []) + operation.get("parameters", [])

    for p in all_params:
        if not isinstance(p, dict):
            continue

        name = p.get("name", "")
        if not name:
            continue

        location_str = p.get("in", "query")
        location_map = {
            "path": ParamLocation.PATH,
            "query": ParamLocation.QUERY,
            "header": ParamLocation.HEADER,
        }
        location = location_map.get(location_str, ParamLocation.QUERY)

        # Determine type from schema
        schema = p.get("schema", {})
        raw_type = schema.get("type", "string") if isinstance(schema, dict) else "string"
        param_type = _openapi_type_to_param_type(raw_type)

        # Extract enum values
        enum_values = schema.get("enum") if isinstance(schema, dict) else None

        params.append(
            RouteParam(
                name=name,
                location=location,
                param_type=param_type,
                raw_type=raw_type,
                required=p.get("required", location == ParamLocation.PATH),
                description=p.get("description", ""),
                enum_values=enum_values,
            )
        )

    # Handle request body (OpenAPI 3.x)
    request_body = operation.get("requestBody", {})
    if isinstance(request_body, dict):
        content = request_body.get("content", {})
        for _media_type, media_obj in content.items():
            if not isinstance(media_obj, dict):
                continue
            schema = media_obj.get("schema", {})
            if isinstance(schema, dict) and schema.get("properties"):
                for prop_name, prop_schema in schema["properties"].items():
                    raw_type = prop_schema.get("type", "string")
                    required_list = schema.get("required", [])
                    params.append(
                        RouteParam(
                            name=prop_name,
                            location=ParamLocation.BODY,
                            param_type=_openapi_type_to_param_type(raw_type),
                            raw_type=raw_type,
                            required=prop_name in required_list,
                            description=prop_schema.get("description", ""),
                        )
                    )
            break  # Only process first content type

    return params


def _extract_response_info(
    operation: dict,
) -> tuple[ResponseFormat, str, dict | None]:
    """Extract response format, model name, and schema from an OpenAPI operation.

    Reads the responses section to determine content-type and schema.
    Returns (format, model_name, schema_dict).
    """
    responses = operation.get("responses", {})
    # Look at success responses (200, 201, 2xx)
    for status in ("200", "201", "202", "default"):
        resp = responses.get(status)
        if not isinstance(resp, dict):
            continue

        content = resp.get("content", {})
        for content_type, media_obj in content.items():
            # Determine format from content-type
            resp_format = CONTENT_TYPE_MAP.get(content_type, ResponseFormat.JSON)

            # Extract schema info
            schema = media_obj.get("schema", {}) if isinstance(media_obj, dict) else {}
            model_name = ""
            resp_schema = None

            if isinstance(schema, dict):
                # Get model name from $ref or title
                ref = schema.get("$ref", "")
                if ref:
                    model_name = ref.split("/")[-1]
                elif schema.get("title"):
                    model_name = schema["title"]
                elif schema.get("type") == "array" and isinstance(schema.get("items"), dict):
                    item_ref = schema["items"].get("$ref", "")
                    if item_ref:
                        model_name = f"List[{item_ref.split('/')[-1]}]"

                # Capture schema if it has useful structure
                if schema.get("properties") or schema.get("$ref") or schema.get("items"):
                    resp_schema = schema

            return resp_format, model_name, resp_schema

    return ResponseFormat.JSON, "", None


def _openapi_type_to_param_type(openapi_type: str) -> ParamType:
    """Map OpenAPI type strings to ParamType."""
    mapping = {
        "string": ParamType.STRING,
        "integer": ParamType.INTEGER,
        "number": ParamType.FLOAT,
        "boolean": ParamType.BOOLEAN,
        "array": ParamType.LIST,
        "object": ParamType.JSON,
        "file": ParamType.FILE,
    }
    return mapping.get(openapi_type, ParamType.STRING)


def _path_to_name(method: str, path: str) -> str:
    """Generate a function name from method + path."""
    segments = [s for s in path.strip("/").split("/") if s and not s.startswith("{")]
    name = "_".join(segments) if segments else "root"
    return f"{method}_{name}"


def parse_openapi(repo_root: Path) -> tuple[list[ParsedRoute], list[ParseWarning]]:
    """Parse all OpenAPI specs in a repository."""
    all_routes: list[ParsedRoute] = []
    all_warnings: list[ParseWarning] = []

    spec_files = find_spec_files(repo_root)
    if not spec_files:
        return all_routes, all_warnings

    for spec_path in spec_files:
        logger.info("Parsing OpenAPI spec: %s", spec_path)
        routes, warnings = parse_spec_file(spec_path)
        all_routes.extend(routes)
        all_warnings.extend(warnings)

    return all_routes, all_warnings
