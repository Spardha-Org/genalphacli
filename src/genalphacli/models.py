"""Data models for the API parser pipeline.

Internal intermediate representation (ParsedRoute) and final output (CommandGraph).
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ── Enums ──────────────────────────────────────────────────────


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ParamLocation(str, Enum):
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    BODY = "body"


class ParamType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    FLOAT = "float"
    LIST = "list"
    FILE = "file"
    JSON = "json"


class SourceLayer(int, Enum):
    UNKNOWN = 0
    OPENAPI = 1
    AST = 2
    LLM = 3


class AuthType(str, Enum):
    BEARER = "bearer"
    API_KEY = "api_key"
    NONE = "none"


# ── Type Mapping ───────────────────────────────────────────────

TYPE_MAP: dict[str, ParamType] = {
    # Python types
    # Python primitives
    "str": ParamType.STRING,
    "int": ParamType.INTEGER,
    "bool": ParamType.BOOLEAN,
    "float": ParamType.FLOAT,
    "list": ParamType.LIST,
    "List": ParamType.LIST,
    "UploadFile": ParamType.FILE,
    "Optional": ParamType.STRING,
    # Python stdlib types that map to string
    "UUID": ParamType.STRING,
    "uuid": ParamType.STRING,
    "datetime": ParamType.STRING,
    "date": ParamType.STRING,
    "time": ParamType.STRING,
    "timedelta": ParamType.STRING,
    "Decimal": ParamType.STRING,
    "Path": ParamType.STRING,
    "bytes": ParamType.STRING,
    "Any": ParamType.STRING,
    # Common Pydantic / FastAPI types
    "EmailStr": ParamType.STRING,
    "HttpUrl": ParamType.STRING,
    "AnyUrl": ParamType.STRING,
    "IPvAnyAddress": ParamType.STRING,
    "SecretStr": ParamType.STRING,
    # Python numeric types
    "complex": ParamType.FLOAT,
    # Python collection types
    "dict": ParamType.JSON,
    "Dict": ParamType.JSON,
    "set": ParamType.LIST,
    "Set": ParamType.LIST,
    "tuple": ParamType.LIST,
    "Tuple": ParamType.LIST,
    "Sequence": ParamType.LIST,
    # Java types (Phase 3+)
    "String": ParamType.STRING,
    "Integer": ParamType.INTEGER,
    "Long": ParamType.INTEGER,
    "Boolean": ParamType.BOOLEAN,
    "Double": ParamType.FLOAT,
    "MultipartFile": ParamType.FILE,
}


def resolve_type(raw_type: str) -> ParamType:
    """Map a raw type string to a ParamType, defaulting to JSON for unknowns."""
    # Handle generic types like List[str], Optional[int]
    base = raw_type.split("[")[0].strip()
    return TYPE_MAP.get(base, ParamType.JSON)


# ── Internal Route Model (Intermediate Representation) ─────────


class RouteParam(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    location: ParamLocation
    param_type: ParamType = ParamType.STRING
    raw_type: str = ""
    required: bool = True
    description: str = ""
    default: str | None = None
    enum_values: list[str] | None = None


class ResponseFormat(str, Enum):
    JSON = "json"
    HTML = "html"
    TEXT = "text"
    XML = "xml"
    BINARY = "binary"
    FILE = "file"
    STREAM = "stream"


# Map content-types and FastAPI response classes to ResponseFormat
CONTENT_TYPE_MAP: dict[str, ResponseFormat] = {
    "application/json": ResponseFormat.JSON,
    "text/html": ResponseFormat.HTML,
    "text/plain": ResponseFormat.TEXT,
    "application/xml": ResponseFormat.XML,
    "text/xml": ResponseFormat.XML,
    "application/octet-stream": ResponseFormat.BINARY,
}

RESPONSE_CLASS_MAP: dict[str, ResponseFormat] = {
    "JSONResponse": ResponseFormat.JSON,
    "HTMLResponse": ResponseFormat.HTML,
    "PlainTextResponse": ResponseFormat.TEXT,
    "FileResponse": ResponseFormat.FILE,
    "StreamingResponse": ResponseFormat.STREAM,
    "Response": ResponseFormat.BINARY,
    "RedirectResponse": ResponseFormat.TEXT,
    "ORJSONResponse": ResponseFormat.JSON,
    "UJSONResponse": ResponseFormat.JSON,
}


class ParsedRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: HttpMethod
    path: str
    function_name: str
    description: str = ""
    params: list[RouteParam] = []
    response_format: ResponseFormat = ResponseFormat.JSON
    response_model: str = ""
    response_schema: dict | None = None
    source_file: Path | None = None
    source_layer: SourceLayer = SourceLayer.UNKNOWN
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    service_name: str = ""


# ── Parse Metadata ─────────────────────────────────────────────


class ParseWarning(BaseModel):
    message: str
    source_file: str = ""
    layer: SourceLayer = SourceLayer.UNKNOWN
    severity: Literal["info", "warning", "error"] = "warning"


class ParseMetadata(BaseModel):
    warnings: list[ParseWarning] = []
    total_routes: int = 0
    layer_counts: dict[str, int] = {}
    files_scanned: int = 0
    parse_time_ms: int = 0


# ── Command Graph (Final Output) ──────────────────────────────


class AuthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: AuthType = AuthType.NONE
    env_var: str = ""


class CommandParam(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    flag: str
    type: ParamType = ParamType.STRING
    required: bool = True
    description: str = ""
    default: str | None = None
    enum_values: list[str] | None = None


class OutputConfig(BaseModel):
    format: ResponseFormat = ResponseFormat.JSON
    content_type: str = ""
    response_model: str = ""
    response_schema: dict | None = None


class Subcommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    method: HttpMethod
    endpoint: str
    params: list[CommandParam] = []
    output: OutputConfig = OutputConfig()


class CommandGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0.0"
    command: str
    version: str = "0.1.0"
    base_url: str = ""
    auth: AuthConfig = AuthConfig()
    subcommands: list[Subcommand] = []
    metadata: ParseMetadata = ParseMetadata()


# ── Build Config (CLI Generator) ──────────────────────────────


class DistributionType(str, Enum):
    PIP = "pip"


class BuildConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cli_name: str
    base_url: str
    auth: AuthConfig = AuthConfig()
    distribution: DistributionType = DistributionType.PIP

    @field_validator("cli_name")
    @classmethod
    def validate_cli_name(cls, v: str) -> str:
        import re

        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                "cli_name must be a valid Python identifier "
                "(lowercase letters, digits, underscores, must start with letter)"
            )
        return v

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        import ipaddress
        from urllib.parse import urlparse

        parsed = urlparse(v)
        if parsed.scheme not in ("https", "http"):
            raise ValueError("base_url must use https:// or http://")
        if not parsed.hostname:
            raise ValueError("base_url must have a hostname")
        # Block private/loopback IPs
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            if ip.is_private or ip.is_loopback:
                raise ValueError(f"base_url cannot target private/loopback IP: {parsed.hostname}")
        except ValueError as e:
            if "private" in str(e) or "loopback" in str(e):
                raise
            # hostname is a domain name, not an IP — that's fine
        return v.rstrip("/")
