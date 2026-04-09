"""Data models for the API parser pipeline.

Internal intermediate representation (ParsedRoute) and final output (CommandGraph).
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
    "str": ParamType.STRING,
    "int": ParamType.INTEGER,
    "bool": ParamType.BOOLEAN,
    "float": ParamType.FLOAT,
    "list": ParamType.LIST,
    "List": ParamType.LIST,
    "UploadFile": ParamType.FILE,
    "Optional": ParamType.STRING,
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


class ParsedRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: HttpMethod
    path: str
    function_name: str
    description: str = ""
    params: list[RouteParam] = []
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
    format: str = "json"


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
