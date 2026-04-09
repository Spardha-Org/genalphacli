# GenAlpha CLI

Convert any API repository into a working, installable CLI tool — automatically.

GenAlpha CLI parses a GitHub repository, extracts all API routes via static analysis, and generates a standalone CLI that makes real API calls. No manual wiring. No Postman. Just `parse → build → use`.

## The Full Loop

```
                         PARSE                              BUILD                         USE
                ┌─────────────────────┐          ┌──────────────────────┐       ┌──────────────────┐
GitHub URL ───> │ Clone + Detect      │          │ Jinja2 Templates     │       │ Installed CLI     │
   or           │ OpenAPI Spec Parse  │ ──JSON── │ Typer CLI Generation │ ───>  │ Real API Calls    │
Local Path ───> │ AST Route Extract   │  graph   │ HTTP Client + Auth   │  pip  │ Auth + Errors     │
                └─────────────────────┘          └──────────────────────┘       └──────────────────┘

$ genalphacli parse owner/repo -o graph.json
$ genalphacli build graph.json -n myapi --base-url https://api.example.com
$ cd dist/myapi && pip install .
$ myapi list-users --limit 5
```

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Git

### Installation

```bash
git clone https://github.com/NandishNaik01/genalphacli.git
cd genalphacli
uv sync
```

### Step 1: Parse a Repository

```bash
# From GitHub
uv run genalphacli parse owner/repo -o graph.json

# From a local directory
uv run genalphacli parse-local ./my-fastapi-app -o graph.json

# Detect framework only
uv run genalphacli detect owner/repo
```

### Step 2: Build a CLI

```bash
uv run genalphacli build graph.json \
  --name myapi \
  --base-url https://api.example.com \
  --auth-type bearer \
  --auth-env-var MYAPI_TOKEN
```

This generates a complete pip package at `dist/myapi/`.

### Step 3: Install and Use

```bash
cd dist/myapi && uv pip install .

# Now use it from anywhere
myapi --help
myapi list-users --limit 5
myapi get-user abc123
myapi create-user --name "John" --email "john@test.com"
myapi create-user --body '{"name": "John", "email": "john@test.com", "role": "admin"}'
```

### GitHub Authentication

For private repositories or to avoid API rate limits:

```bash
export GITHUB_TOKEN=your_github_token
uv run genalphacli parse owner/private-repo -o graph.json
```

## What Gets Generated

The `build` command produces a complete, installable Python package:

```
dist/myapi/
├── pyproject.toml          # pip-installable with entry point
├── src/myapi/
│   ├── __init__.py
│   ├── cli.py              # Typer CLI with all commands
│   ├── client.py           # HTTP client with auth + error handling
│   └── _graph.json         # Embedded command graph
```

### Generated CLI Features

- **Path params as positional args**: `myapi get-user abc123` (not `--user-id abc123`)
- **Body fields as flags**: `myapi create-user --name John --email j@test.com`
- **Raw JSON override**: `myapi create-user --body '{"name": "John"}'` bypasses flags
- **Pretty output**: `myapi list-users --pretty` for Rich-formatted JSON
- **Friendly errors**: `401 → "Authentication failed. Set MYAPI_TOKEN env var."`
- **Env-overridable base URL**: Set `MYAPI_BASE_URL` for staging/dev/prod
- **Auth via env var**: Bearer token or API key from environment variable

### Error Handling

| HTTP Status | CLI Message |
|---|---|
| 401 | `Authentication failed. Set MYAPI_TOKEN environment variable.` |
| 403 | `Permission denied.` |
| 404 | `Resource not found.` |
| 422 | `Validation error: {details}` |
| 429 | `Rate limited. Try again later.` |
| 5xx | `API error {status}: {body}` |

## Parsing Pipeline

Two-layer parsing strategy with auto-detection of base URL and auth.

### Layer 1: OpenAPI Spec Detection

Scans for `openapi.json`, `swagger.yaml`, and similar files. If found, parses directly.

- Supports OpenAPI v3 and Swagger v2
- Resolves internal `$ref` references (remote URLs blocked for security)
- Extracts response schemas and content types

### Layer 2: AST-Based Route Extraction

Uses Python's `ast` module to extract routes from decorators and type annotations.

| Framework | Decorator Patterns | Status |
|---|---|---|
| FastAPI | `@app.get()`, `@router.post()`, `@app.api_route()` | Supported |
| Flask | `@app.route()`, `@blueprint.route()` | Planned |
| Django/DRF | `path()`, `@api_view()`, `ViewSet` | Planned |
| Spring Boot | `@GetMapping`, `@PostMapping` | Planned |

**Handles complex patterns:**

- Cross-file `include_router(router, prefix="/api/v1")` prefix resolution via import tracking
- `APIRouter(prefix="/users")` router-level prefixes
- Async handlers, docstrings, constant propagation
- Pydantic model schema extraction for response models

**Automatically filters out:**

- FastAPI dependency injection (`Depends()`, `Annotated[X, Depends()]`, `*Dep` suffix types)
- Common DI names (`session`, `db`, `current_user`, `authorization`, `request`, `response`)
- Framework internals (`Request`, `Response`, `BackgroundTasks`)

### Auto-Detection

| Signal | Source | Priority |
|---|---|---|
| Auth type (bearer/api_key) | `.env.example` + code patterns (`HTTPBearer`, `OAuth2`) | Auto-detected |
| Base URL | `.env.example` (`BASE_URL`, `API_URL`, `PORT`) | Auto-detected |
| CLI overrides (`--base-url`, `--auth-type`) | User flags | Highest |

### Response Format Detection

Response formats are detected from OpenAPI content-types and FastAPI `response_class`/`response_model`:

| Source | Detected Format |
|---|---|
| `application/json` / default | `json` |
| `text/html` / `HTMLResponse` | `html` |
| `text/plain` / `PlainTextResponse` | `text` |
| `FileResponse` | `file` |
| `StreamingResponse` | `stream` |
| `response_model=UserOut` | Full schema with field types |

## Type Mapping

| Python Type | CLI Flag Type | Flag Behavior |
|---|---|---|
| `str`, `UUID`, `EmailStr`, `datetime` | `string` | `--flag VALUE` |
| `int` | `integer` | `--flag N` |
| `bool` | `boolean` | `--flag` (toggle) |
| `float`, `Decimal` | `float` | `--flag N.N` |
| `list`, `List[X]`, `set`, `tuple` | `list` | `--flag a,b,c` |
| `UploadFile` | `file` | `--flag @filepath` |
| Pydantic models, `dict` | `json` | `--flag '{"key": "value"}'` |

## Security

### Parser Security

- **Git hooks disabled**: `--no-checkout` + `.gitattributes` filter driver sanitization + checkout
- **No code execution**: `ast.parse()` only — never `import`, `eval`, or `exec`
- **Repo size cap**: Rejects repositories larger than 500MB
- **Remote `$ref` blocked**: OpenAPI parser uses `RESOLVE_INTERNAL` only
- **URL validation**: `urlparse()` rejects ports, userinfo, non-ASCII, fragments
- **Temp file isolation**: `~/.cache/genalphacli/` with `0700` permissions + atexit cleanup

### Generator Security

- **Jinja2 SandboxedEnvironment**: Prevents template injection from malicious graph.json
- **String sanitization**: All graph values escaped before template rendering
- **AST safety walk**: Post-generation scan rejects `eval`, `exec`, `os.system`, `subprocess`
- **`cli_name` validation**: Must match `^[a-z][a-z0-9_]*$` (safe Python identifier)
- **`base_url` validation**: Rejects private/loopback IPs and `file://` scheme
- **Token CRLF prevention**: Generated client rejects tokens with `\r\n\0`

## CLI Reference

```
genalphacli [COMMAND] [OPTIONS]
```

### Commands

| Command | Description |
|---|---|
| `parse <github-url>` | Clone a GitHub repo, parse it, output command graph JSON |
| `parse-local <path>` | Parse a local directory |
| `detect <github-url>` | Detect the API framework used |
| `build <graph.json>` | Generate an installable CLI from a command graph |

### Parse Options

| Flag | Description |
|---|---|
| `--output`, `-o` | Write JSON to a file |
| `--base-url` | API base URL override |
| `--auth-type` | Auth type: `bearer`, `api_key`, `none` |
| `--auth-env-var` | Env var name for auth token |
| `--verbose`, `-v` | Show progress and statistics |

### Build Options

| Flag | Description |
|---|---|
| `--name`, `-n` | CLI command name (required) |
| `--base-url` | API base URL (required) |
| `--output-dir`, `-d` | Output directory (default: `dist`) |
| `--auth-type` | Auth type override |
| `--auth-env-var` | Auth env var name override |

## Project Structure

```
src/genalphacli/
  cli.py                    # Typer CLI entry point (parse, build, detect)
  config.py                 # Environment variable management
  config_detector.py        # Auto-detect base_url and auth from repo
  github.py                 # GitHub API, secure clone, framework detection
  models.py                 # Pydantic data models, enums, type mapping
  pipeline.py               # Pipeline orchestrator, route merger, graph builder
  parsers/
    __init__.py             # FrameworkParser protocol + registry
    openapi_parser.py       # Layer 1: OpenAPI/Swagger spec parsing
    fastapi_parser.py       # Layer 2: FastAPI AST-based extraction
    model_extractor.py      # Pydantic model schema resolution
  generators/
    __init__.py             # Jinja2 SandboxedEnvironment factory
    pip_generator.py        # Generates pip-installable CLI packages
    templates/pip_package/  # Jinja2 templates (cli.py, client.py, pyproject.toml)
```

## Development

### Setup

```bash
git clone https://github.com/NandishNaik01/genalphacli.git
cd genalphacli
uv sync --group dev
```

### Run Tests

```bash
uv run pytest -v          # 74 tests, ~0.5s
```

### Lint and Format

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

### Run Mock Server (for live testing)

```bash
uv run uvicorn tests.mock_server.server:app --port 9999
```

## Real-World Test Results

| Repository | Routes Found | Parse Time |
|---|---|---|
| `tiangolo/full-stack-fastapi-template` | 23 routes | 39ms |
| `sai-life-sciences` (6 route files, nested imports) | 17/17 routes | 35ms |
| `testdrivenio/fastapi-crud-async` | 6 routes | 6ms |
| Mock server (10 endpoints, live API calls) | 10/10 passing | - |

## Roadmap

- [x] **Phase 1**: FastAPI + OpenAPI parser pipeline
- [x] **CLI Generator**: graph.json to installable pip package
- [x] **Live API Testing**: Mock server + end-to-end verification
- [ ] **Phase 2**: Flask and Django/DRF support
- [ ] **Phase 3**: Java (Spring Boot) support via tree-sitter
- [ ] **MCP Server Generator**: Expose APIs as MCP tools for AI agents
- [ ] **Standalone Script**: Zero-dependency single-file CLI option

## License

MIT
