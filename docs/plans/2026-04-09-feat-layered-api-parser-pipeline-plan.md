---
title: "feat: Layered API Parser Pipeline"
type: feat
status: active
date: 2026-04-09
---

# feat: Layered API Parser Pipeline

## Enhancement Summary

**Deepened on:** 2026-04-09
**Research agents used:** 8 (Python reviewer, Security sentinel, Performance oracle, Architecture strategist, Simplicity reviewer, Pattern recognition, Framework docs researcher, Best practices researcher)

### Key Improvements
1. **Restructured into MVP-aligned phases** — Phase 1 is now FastAPI + OpenAPI only (per PRD), with Flask/Django/Spring Boot deferred to later phases
2. **Hardened security model** — git clone via `subprocess` with `--no-checkout` sanitize flow, prance remote `$ref` blocking, LLM opt-in (not opt-out)
3. **Formalized parser plugin system** — `FrameworkParser` protocol enables adding frameworks without modifying orchestration code
4. **Strengthened type safety** — all magic ints/strings replaced with enums, modern `X | None` syntax, Pydantic v2 validators and `ConfigDict`
5. **Performance architecture** — single-pass file indexing, lazy imports for heavy deps, file content cache across layers

### New Considerations Discovered
- GitPython's `core.hooksPath=/dev/null` is insufficient — `.gitattributes` filter drivers bypass it
- `subprocess.run(["git", ...])` is safer than GitPython for cloning (smaller attack surface)
- prance fetches remote `$ref` URLs by default — must be restricted to local-only
- LLM prompt injection extends beyond comments into string literals, docstrings, and filenames
- The 500ms CLI overhead target is unrealistic as stated — Typer+Rich imports alone take 200-300ms

---

## Overview

Build a Python-based layered parser pipeline that clones a GitHub repository, detects the API framework, and extracts API routes through a multi-layer parsing chain, producing a structured command graph JSON that powers CLI generation.

## Problem Statement

Developers lack a standardized way to convert API repositories into CLI tools. The parser pipeline is the core engine — it must reliably extract API routes, parameters, and metadata from codebases using static analysis, without executing any code.

## Proposed Solution

A layered pipeline where each layer handles progressively harder parsing cases. OpenAPI specs are the fast path, AST handles standard routes, and LLM catches the long tail. Later layers override earlier ones on conflicts. Built incrementally — FastAPI first, then expand.

## Technical Stack

| Component | Library | Version | Notes |
|---|---|---|---|
| OpenAPI parsing | `prance[osv]` + `openapi-spec-validator` | latest | Configure to reject remote `$ref` URLs |
| Python AST | `ast` (stdlib) | N/A | Zero-dep, handles all valid Python |
| Java AST | `tree-sitter` + `tree-sitter-language-pack` | 0.25.x | Phase 3+ only; lazy-import to avoid startup cost |
| Git operations | `subprocess` (stdlib) | N/A | Safer than GitPython; full control over args |
| GitHub API | `requests` (for metadata) | latest | Single endpoint call; PyGithub is overkill |
| CLI framework | `Typer` + `Rich` | 0.21.x | Dynamic command generation via `inspect.Signature` |
| Data models | `pydantic` | 2.x | v2 validators, discriminated unions, `ConfigDict` |
| LLM (fallback) | Anthropic SDK | latest | Phase 4+ only; opt-in via `--use-llm` flag |

### Research Insights: Stack Decisions

- **`subprocess` over GitPython:** GitPython has had repeated CVEs (CVE-2022-24439, CVE-2023-40267, CVE-2023-41040) related to argument injection. `subprocess.run(["git", "clone", ...])` with a fully controlled argument list eliminates this surface. No extra dependency.
- **`requests` over PyGithub:** We only need the `/repos/{owner}/{repo}/languages` endpoint. A single `requests.get()` call is lighter than importing PyGithub's entire object model.
- **tree-sitter over javalang:** javalang is abandoned (last update 2020, Java 8 only). tree-sitter supports all Java versions, is error-tolerant, and is used by GitHub/Neovim/Zed.
- **Typer dynamic commands:** Use `inspect.Signature` manipulation + `app.command(name=...)(fn)` factory pattern to generate CLI commands from parsed data at runtime. Avoids the closure-in-loop bug.

## Architecture

### Phase 1 (MVP) Architecture — FastAPI + OpenAPI only

```
src/
  genalphacli/
    __init__.py
    cli.py                    # Typer CLI entry point
    config.py                 # Settings, env vars, defaults
    models.py                 # All Pydantic models (single file for MVP)
    github.py                 # Clone repo, fetch metadata, temp dir mgmt
    pipeline.py               # Orchestrates parsing layers + builds graph
    parsers/
      __init__.py             # FrameworkParser protocol definition
      openapi_parser.py       # Layer 1: OpenAPI/Swagger spec parsing
      fastapi_parser.py       # Layer 2: FastAPI AST-based route extraction
tests/
  fixtures/
    fastapi_simple/           # Basic FastAPI app with simple routes
    fastapi_complex/          # Router includes, variable prefixes
    openapi_v3/               # Standard OpenAPI v3 spec
  test_github.py
  test_openapi_parser.py
  test_fastapi_parser.py
  test_pipeline.py
```

### Full Architecture (Phase 3+) — Multi-framework

```
src/
  genalphacli/
    __init__.py
    cli.py
    config.py
    models.py
    github.py
    pipeline.py               # Cross-package orchestrator (not inside parsers/)
    file_index.py             # Single-pass file discovery + content cache
    parsers/
      __init__.py             # FrameworkParser protocol + registry
      openapi_parser.py       # Layer 1
      llm_parser.py           # Layer 3 (opt-in)
      frameworks/
        fastapi_parser.py     # FastAPI regex + AST
        flask_parser.py       # Flask regex + AST
        django_parser.py      # Django/DRF regex + AST
        spring_boot_parser.py # Spring Boot tree-sitter AST
tests/
  fixtures/
    fastapi_simple/
    fastapi_complex/
    flask_simple/
    django_drf/
    spring_boot_simple/
    spring_boot_complex/
    openapi_v2/
    openapi_v3/
  parsers/
    test_openapi_parser.py
    test_fastapi_parser.py
    test_flask_parser.py
    ...
  test_github.py
  test_pipeline.py
```

### Research Insights: Architecture Decisions

- **`pipeline.py` at top level, not inside `parsers/`** — it coordinates across packages (parsers, github, models), so it should be a peer, not nested inside one of its dependencies.
- **No separate `merger/`, `type_mapping/`, `output/`, `detection/` directories** — for MVP these are functions, not modules. A `TYPE_MAP` dict in `models.py`, a `merge_routes()` function in `pipeline.py`, a `to_command_graph()` method on the model. Directories come when complexity demands them.
- **Test structure mirrors source** — `tests/parsers/test_fastapi_parser.py` matches `src/genalphacli/parsers/fastapi_parser.py`.
- **Each framework parser owns both regex and AST logic** — avoids scattering framework knowledge across layer files. The `FrameworkParser` protocol declares both methods.

## Data Models

### Research Insights: Model Design

- Use modern `X | None` syntax (Python 3.10+), not `Optional[X]`
- All magic integers/strings replaced with enums
- `Field(ge=0.0, le=1.0)` for confidence validation
- `ConfigDict(extra="forbid")` catches typos in field names
- `raw_type` field on `RouteParam` enables centralized type mapping in the graph builder
- `schema_version` on `CommandGraph` distinct from CLI version — downstream consumers need this

```python
# src/genalphacli/models.py
from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Self


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
    AST = 2        # regex removed; AST is primary for MVP
    LLM = 3


class AuthType(str, Enum):
    BEARER = "bearer"
    API_KEY = "api_key"
    NONE = "none"


# ── Type Mapping Table ─────────────────────────────────────────

TYPE_MAP: dict[str, ParamType] = {
    # Python types
    "str": ParamType.STRING,
    "int": ParamType.INTEGER,
    "bool": ParamType.BOOLEAN,
    "float": ParamType.FLOAT,
    "list": ParamType.LIST,
    "List": ParamType.LIST,
    "UploadFile": ParamType.FILE,
    # Java types (Phase 3+)
    "String": ParamType.STRING,
    "Integer": ParamType.INTEGER,
    "Long": ParamType.INTEGER,
    "Boolean": ParamType.BOOLEAN,
    "Double": ParamType.FLOAT,
    "MultipartFile": ParamType.FILE,
}


# ── Internal Route Model (Intermediate Representation) ─────────

class RouteParam(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    location: ParamLocation
    param_type: ParamType = ParamType.STRING
    raw_type: str = ""                     # original type string before mapping
    required: bool = True
    description: str = ""
    default: str | None = None
    enum_values: list[str] | None = None


class ParsedRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: HttpMethod
    path: str                              # e.g., "/users/{id}"
    function_name: str                     # e.g., "get_user"
    description: str = ""                  # from docstring or annotation
    params: list[RouteParam] = []
    source_file: Path | None = None        # file where route was found
    source_layer: SourceLayer = SourceLayer.UNKNOWN
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    service_name: str = ""                 # for monorepo grouping (Phase 3+)


# ── Parse Metadata ─────────────────────────────────────────────

class ParseWarning(BaseModel):
    message: str
    source_file: str = ""
    layer: SourceLayer = SourceLayer.UNKNOWN
    severity: Literal["info", "warning", "error"] = "warning"


class ParseMetadata(BaseModel):
    warnings: list[ParseWarning] = []
    total_routes: int = 0
    layer_counts: dict[str, int] = {}      # {"OPENAPI": 5, "AST": 12}
    files_scanned: int = 0
    parse_time_ms: int = 0


# ── Command Graph (Final Output) ──────────────────────────────

class AuthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: AuthType = AuthType.NONE
    env_var: str = ""                      # var NAME only, never the value


class CommandParam(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    flag: str                              # e.g., "--user-id"
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
    endpoint: str                          # e.g., "/users/{id}"
    params: list[CommandParam] = []
    output: OutputConfig = OutputConfig()


class CommandGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0.0"          # schema format version
    command: str                           # CLI name
    version: str = "0.1.0"                 # CLI version
    base_url: str = ""
    auth: AuthConfig = AuthConfig()
    subcommands: list[Subcommand] = []
    metadata: ParseMetadata = ParseMetadata()
```

### Parser Protocol

```python
# src/genalphacli/parsers/__init__.py
from typing import Protocol
from pathlib import Path
from genalphacli.models import ParsedRoute, DetectedFramework


class FrameworkParser(Protocol):
    """Contract all framework parsers must implement."""

    @property
    def framework_name(self) -> str: ...

    def supported_extensions(self) -> list[str]: ...

    def parse(self, files: list[Path], repo_root: Path) -> list[ParsedRoute]: ...

    def should_run(self, detected: DetectedFramework) -> bool: ...


# Registry — new frameworks register here
PARSER_REGISTRY: dict[str, FrameworkParser] = {}


def register_parser(parser: FrameworkParser) -> None:
    PARSER_REGISTRY[parser.framework_name] = parser
```

## Implementation Phases

### Phase 1: MVP — FastAPI + OpenAPI (matches PRD Phase 1)

**Goal:** End-to-end pipeline for FastAPI repos. OpenAPI spec parsing + Python AST extraction. No regex layer (AST handles FastAPI decorators directly and more accurately).

#### Tasks

- [ ] Initialize Python project with `pyproject.toml` (Python 3.10+)
  - Dependencies: `typer[all]`, `prance[osv]`, `openapi-spec-validator`, `pydantic>=2.0`, `requests`
  - Dev dependencies: `pytest`, `pytest-cov`, `ruff`, `hypothesis`
  - **No tree-sitter, no LLM SDK, no PyGithub, no GitPython** — not needed for Phase 1
- [ ] Create all Pydantic models in `models.py` (as defined above)
  - All enums, typed dicts, `ConfigDict(extra="forbid")`, `Field` validators
- [ ] Build GitHub module (`github.py`):
  - Parse GitHub URL with `urllib.parse.urlparse()` — validate scheme=`https`, netloc=`github.com`, path matches `/{owner}/{repo}`, reject `@`/ports/non-ASCII
  - Fetch repo metadata via `requests.get("https://api.github.com/repos/{owner}/{repo}")` — languages, size, description
  - **Security:** Check `repo.size` (KB) against 500MB limit before cloning
  - Clone via `subprocess.run(["git", "clone", "--no-checkout", "--depth", "1", "--single-branch", "--config", "core.hooksPath=/dev/null", "--config", "core.fsmonitor=false", "--no-recurse-submodules", url, target])` then sanitize then `git checkout`
  - **Security:** After `--no-checkout`, scan for `.gitattributes` filter drivers and remove before checkout
  - **Security:** Monitor disk usage during clone, abort if exceeds 500MB
  - Temp dir: `~/.cache/genalphacli/` with `0o700` permissions + `atexit` cleanup handler
  - Detect framework: check `requirements.txt`/`pyproject.toml` for `fastapi` dependency
- [ ] Build OpenAPI parser (`parsers/openapi_parser.py`):
  - Scan for spec files: `openapi.json`, `openapi.yaml`, `swagger.json`, `swagger.yaml` in root, `/docs`, `/api-docs`, `/specs`
  - Use `prance.ResolvingParser` with `resolve_types=RESOLVE_INTERNAL` only — **block remote `$ref` URLs**
  - Fallback: if full resolution fails, use `prance.BaseParser` for partial results + warnings
  - Walk `paths` dict to extract routes, params, descriptions
  - Produce `list[ParsedRoute]` with `source_layer=SourceLayer.OPENAPI`
- [ ] Build FastAPI AST parser (`parsers/fastapi_parser.py`):
  - Implement `FrameworkParser` protocol
  - Use `ast.parse()` + `ast.NodeVisitor` to extract:
    - `@app.get("/path")`, `@app.post(...)`, `@router.get(...)` decorators
    - Function signatures for params with type hints → map via `TYPE_MAP`
    - Handle both `FunctionDef` and `AsyncFunctionDef`
    - Basic constant propagation for variable paths
    - Resolve `include_router(router, prefix=X)` across files
  - Produce `list[ParsedRoute]` with `source_layer=SourceLayer.AST`
- [ ] Build pipeline orchestrator (`pipeline.py`):
  - Single-pass file indexing: `os.scandir()` walk respecting `.gitignore`, categorize by extension
  - File content cache: `dict[Path, str]` populated lazily, shared across layers
  - Run Layer 1 (OpenAPI) → always run Layer 2 (AST) as validation pass even if spec found
  - Merge results: route identity = `(http_method, normalized_path)` with path params as wildcards
  - Later layer wins on conflict (full replacement)
  - Build `CommandGraph` from merged routes — apply type mapping, generate flag names (`snake_case` → `--kebab-case`)
- [ ] Build Typer CLI (`cli.py`):
  - `genalphacli parse <github-url>` — full pipeline, outputs command graph JSON to stdout
  - `genalphacli parse <github-url> --output graph.json` — write to file
  - `genalphacli detect <github-url>` — detect framework only
  - Options: `--verbose` (progress logging)
  - Rich progress bars for clone, detect, parse steps
  - **Lazy-import Rich** — only import when `--verbose` or progress display is needed
- [ ] Write tests:
  - Unit tests per module
  - Integration test: end-to-end pipeline with FastAPI fixture repos
  - Use `hypothesis` for property-based testing of route merger edge cases
  - Mock `subprocess` and `requests` for github tests — no real network calls

#### Success Criteria

- `genalphacli parse https://github.com/tiangolo/fastapi` produces valid command graph JSON
- OpenAPI parser correctly handles petstore spec (v3)
- AST parser resolves `include_router` prefix composition
- Type mapping covers all Python types from the brainstorm
- Clone completes with hooks disabled, filter drivers removed, temp cleanup works

#### Performance Targets

- CLI startup (import + arg parse): < 300ms
- Layer 1 (OpenAPI parse): < 500ms for typical spec
- Layer 2 (AST parse, < 100 files): < 5 seconds
- Total overhead (excluding clone): < 10 seconds

---

### Phase 2: Flask + Django Support

**Goal:** Add Flask and Django/DRF framework parsers. Extend the `FrameworkParser` protocol.

#### Tasks

- [ ] Build Flask parser (`parsers/frameworks/flask_parser.py`):
  - Implement `FrameworkParser` protocol
  - AST extraction: `@app.route("/path", methods=["GET"])`, `@blueprint.route(...)`
  - Blueprint `url_prefix` resolution across files
- [ ] Build Django/DRF parser (`parsers/frameworks/django_parser.py`):
  - Scan `urls.py` for `path()`, `re_path()`, `url()` calls
  - `@api_view(["GET"])` decorators
  - `ModelViewSet`/`ViewSet` → infer CRUD routes (GET, POST, PUT, PATCH, DELETE)
  - Handle Django's `include()` for nested URL configs
- [ ] Update framework detection in `github.py` for Flask/Django deps
- [ ] Add test fixtures: `flask_simple/`, `django_drf/`

---

### Phase 3: Java (Spring Boot) + Multi-framework

**Goal:** Add Spring Boot support via tree-sitter. Handle monorepos.

#### Tasks

- [ ] Add dependencies: `tree-sitter`, `tree-sitter-language-pack`
- [ ] Build Spring Boot parser (`parsers/frameworks/spring_boot_parser.py`):
  - Lazy-import tree-sitter (only loaded when Java files detected)
  - Tree-sitter S-expression queries for annotation extraction:
    ```
    (annotation
      name: (identifier) @anno.name
      arguments: (annotation_argument_list) @anno.args)
    ```
  - Class-level `@RequestMapping` prefix + method-level path composition
  - `@PathVariable`, `@RequestParam`, `@RequestBody` parameter extraction
  - Handle `value` vs `path` annotation attributes
  - Parse one file at a time, release tree-sitter trees immediately (prevent memory bloat)
  - File-size filter: skip files > 500KB
- [ ] Update framework detection for `pom.xml`/`build.gradle` scanning
- [ ] Add monorepo support:
  - Detect service boundaries by directory-level dependency files
  - Group routes under `ServiceGroup` subcommands
  - Handle command name collisions across services
- [ ] Add Java type mapping to `TYPE_MAP`
- [ ] Add test fixtures: `spring_boot_simple/`, `spring_boot_complex/`, `monorepo_mixed/`

---

### Phase 4: LLM Fallback + Polish

**Goal:** Optional LLM fallback for edge cases. Auth support. Customization.

#### Tasks

- [ ] Build LLM parser (`parsers/llm_parser.py`):
  - **Opt-in only:** requires `--use-llm` flag (not enabled by API key presence alone)
  - Collect unresolved files (framework imports but zero routes from earlier layers)
  - Structured prompt with target JSON schema + example output
  - **Security:** Cap input at 10KB per file, max 5 files per call, max 100K tokens per repo
  - **Security:** Cross-validate ALL LLM routes — function name must exist in source file, path must match code patterns
  - **Security:** Never include `base_url` or auth from LLM output — user-configured only
  - Run LLM calls concurrently via `concurrent.futures.ThreadPoolExecutor`
  - Produce routes with `confidence=0.5-0.7`, flag in metadata
  - If no API key: skip gracefully with warning
- [ ] Auth support (`AuthConfig` in command graph):
  - Bearer token, API key header/query
  - Store env var NAME only, never the value
- [ ] CLI customization:
  - `--depth` flag for nesting depth
  - `--rename` flag for command renaming
- [ ] OpenAPI v2 (Swagger) support in parser
- [ ] Add `genalphacli validate <spec-file>` command

---

## Security Considerations

### Git Clone (Critical — P0)

1. **Clone with `--no-checkout` first, sanitize, then checkout:**
   ```bash
   git clone --no-checkout --depth 1 --single-branch \
     --config core.hooksPath=/dev/null \
     --config core.fsmonitor=false \
     --no-recurse-submodules \
     <url> <target>
   # Scan for .gitattributes filter drivers, remove them
   # Then: git -C <target> checkout
   ```
2. **Block `.gitattributes` filter drivers** — after `--no-checkout`, check for `filter=` directives in `.gitattributes` and strip them before checkout
3. **Use `subprocess.run()` with explicit arg list** — never pass user input through shell interpolation
4. **Set `GIT_TERMINAL_PROMPT=0`** — prevent credential prompts from hanging
5. **Validate URL with `urlparse()`** — reject non-ASCII, ports, userinfo, fragments

### Repo Size & Temp Files (P0)

6. **Pre-check via GitHub API `size` field** — reject repos > 500MB before cloning
7. **Monitor disk during clone** — abort if target directory exceeds 500MB
8. **Temp directory under `~/.cache/genalphacli/`** — not world-readable `/tmp`. Permissions `0o700`.
9. **`atexit` cleanup handler** — catches cases where context manager's `__exit__` doesn't run (SIGKILL)
10. **Startup sweep** — clean stale temp dirs from crashed runs

### OpenAPI Parsing (P1)

11. **Configure prance with `resolve_types=RESOLVE_INTERNAL` only** — blocks remote `$ref` URLs (SSRF risk)
12. **Fallback to `BaseParser`** — if resolution fails, get partial results instead of crashing

### File Scanning (P1)

13. **Reject symlinks** — skip symlinks entirely during file discovery (simpler and safer than resolving)
14. **Never `import`, `eval`, `exec`, or `ast.literal_eval()`** on repo code — `ast.parse()` only
15. **Add ruff/semgrep rule** — ban `eval`, `exec`, `importlib`, `__import__` on repo-derived content in CI

### LLM Layer (P2)

16. **Opt-in only (`--use-llm`)** — default is off. Document data exfiltration implications for private repos.
17. **All LLM output is untrusted** — schema validation is necessary but not sufficient
18. **Cross-validate routes** — every LLM-extracted route must reference a real `source_file` and `function_name` that exist in the repo
19. **Never use LLM-suggested `base_url` or auth** — these come from user config only
20. **Content-length cap** — max 10KB per file sent to LLM

### API Keys (P1)

21. **Environment variables only** — `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`. Never CLI args (visible in `ps`).
22. **Never log key values** — redact in all exception handlers and error messages
23. **`AuthConfig.env_var` stores variable NAME only** — add Pydantic validator to reject values that look like actual tokens

## Non-Functional Requirements

| Metric | Target | Notes |
|---|---|---|
| CLI startup | < 300ms | Lazy-import Rich and tree-sitter |
| Layer 1 (OpenAPI) | < 500ms | For typical spec |
| Layer 2 (AST, < 100 files) | < 5 seconds | With file content cache |
| Layer 3 (tree-sitter) | < 10 seconds | One file at a time, release trees |
| Layer 4 (LLM) | < 30 seconds | Concurrent calls, 5-file max |
| Total (excluding clone) | < 15 seconds | For typical repo |
| Clone (shallow, < 500MB) | < 60 seconds | Network-dependent |
| Memory | < 500MB | tree-sitter file-size filter at 500KB |
| Python version | 3.10+ | Modern syntax, `X \| None` |
| Platforms | macOS, Linux, Windows | `subprocess` for git, no OS-specific deps |

### Research Insights: Performance

- **Single-pass file indexing:** Use `os.scandir()` (faster than `os.walk()`, avoids unnecessary `stat()` calls). Respect `.gitignore` patterns. Categorize files by extension. All layers read from the index, no redundant filesystem walks.
- **File content cache:** `dict[Path, str]` populated lazily on first read. Safe because cloned repo is immutable during analysis. Cap at 50MB, LRU eviction for huge repos.
- **Lazy imports:** `tree-sitter`, `Rich`, LLM SDKs add 100-300ms each on import. Use `importlib.import_module()` to defer until actually needed.
- **Compile regex at module level:** All patterns as `re.compile()` constants. For multi-line matching with `re.DOTALL`, watch for catastrophic backtracking — prefer AST for complex cases.
- **Route merger in O(n):** Dict keyed by `(method, normalized_path)` for constant-time lookup. Never nested loops.
- **tree-sitter memory:** Parse one file at a time, release tree immediately. Skip files > 500KB. A 50KB Java file produces 2-5MB tree; 100 files at once = 300MB.

## Acceptance Criteria

### Functional (Phase 1 MVP)

- [ ] Parses OpenAPI v3 specs into command graph JSON
- [ ] Extracts routes from FastAPI repos via Python AST
- [ ] Resolves `include_router` prefix composition across files
- [ ] Type mapping converts Python types to CLI flag types
- [ ] Route merger deduplicates with `(method, normalized_path)` identity
- [ ] Command graph JSON validates against Pydantic schema with `extra="forbid"`

### Non-Functional (Phase 1 MVP)

- [ ] Git clone uses `--no-checkout` + sanitize + checkout flow
- [ ] `.gitattributes` filter drivers removed before checkout
- [ ] Repo size capped at 500MB (pre-check + runtime monitoring)
- [ ] Temp files under `~/.cache/genalphacli/` with `0o700`, atexit cleanup
- [ ] No code from cloned repos is executed (enforced by linting rule)
- [ ] All Pydantic models use `ConfigDict(extra="forbid")` and enum types

### Functional (Full — Phase 2-4)

- [ ] Extracts routes from Flask, Django/DRF, and Spring Boot repos
- [ ] Monorepo detection produces grouped subcommands
- [ ] LLM fallback handles edge cases when opted-in with `--use-llm`
- [ ] LLM output cross-validated against actual source files
- [ ] Graceful degradation when LLM is unavailable

## Dependencies & Risks

| Risk | Mitigation |
|---|---|
| tree-sitter Java grammar gaps | tree-sitter grammars are community-maintained; test against Java 17+ in Phase 3 |
| FastAPI AST parser misses complex patterns | OpenAPI layer provides baseline; LLM fallback in Phase 4 |
| LLM hallucinated routes | Cross-validation against source files; opt-in only; confidence scoring |
| Large repos exhaust disk/memory | 500MB cap + shallow clone + file-size filters + streaming scan |
| GitHub API rate limits (60/hr unauth) | Cache responses; use token via env var for 5000/hr; graceful error |
| prance remote `$ref` fetching (SSRF) | Configure `resolve_types=RESOLVE_INTERNAL` only |
| `.gitattributes` filter driver execution | `--no-checkout` + sanitize + checkout flow |
| Multi-line decorator regex backtracking | Use AST as primary (not regex); `re.DOTALL` only as pre-filter |
| Typer+Rich import latency (~300ms) | Lazy-import Rich; profile import chain in Phase 1 |

## References

- Brainstorm: `docs/brainstorms/2026-04-09-api-parsing-strategy-brainstorm.md`
- PRD: `prd.md`
- tree-sitter Spring Boot extraction: [Medium article](https://medium.com/@linz07m/extracting-endpoints-and-handlers-from-spring-boot-java-code-using-tree-sitter-73c3481e1b69)
- prance docs: [GitHub](https://github.com/RonnyPfannschmidt/prance)
- Typer docs: [typer.tiangolo.com](https://typer.tiangolo.com/)
- py-tree-sitter 0.25.x: [API docs](https://tree-sitter.github.io/py-tree-sitter/)
- tree-sitter-language-pack: [GitHub](https://github.com/kreuzberg-dev/tree-sitter-language-pack)
- GitPython CVEs: [Snyk](https://security.snyk.io/package/pip/gitpython)
- Pydantic v2 validators: [docs.pydantic.dev](https://docs.pydantic.dev/latest/concepts/validators/)
