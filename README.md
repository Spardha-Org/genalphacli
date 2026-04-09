# GenAlpha CLI

Convert any API repository into a working CLI tool and MCP server — automatically.

GenAlpha CLI parses a GitHub repository, extracts all API routes via static analysis, and generates installable tools that make real API calls. Build a CLI for your terminal or an MCP server for AI agents like Claude and Cursor. No manual wiring. No Postman. Just `parse → build → use`.

## The Full Loop

```
                    PARSE                              BUILD                           USE
           ┌─────────────────────┐          ┌────────────────────────┐       ┌────────────────────┐
GitHub ──> │ Clone + Detect      │          │                        │       │ Terminal CLI        │
  or       │ OpenAPI Spec Parse  │ ──JSON── │  ? Generate:           │       │   myapi list-users  │
Local  ──> │ AST Route Extract   │  graph   │    [x] CLI tool        │ ───>  │                    │
           └─────────────────────┘          │    [x] MCP server      │  pip  │ AI Agents          │
                                            └────────────────────────┘       │   "list all users"  │
                                                                             └────────────────────┘
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
```

### Step 2: Build

```bash
uv run genalphacli build graph.json \
  --name myapi \
  --base-url https://api.example.com

# Interactive prompt:
#   ? Generate:
#     [x] CLI tool
#     [x] MCP server

# Or specify directly:
uv run genalphacli build graph.json -n myapi --base-url https://api.com --type cli
uv run genalphacli build graph.json -n myapi --base-url https://api.com --type mcp
uv run genalphacli build graph.json -n myapi --base-url https://api.com --type cli --type mcp
```

### Step 3: Use

**CLI tool:**

```bash
cd dist/myapi && uv pip install .
myapi --help
myapi list-users --limit 5
myapi get-user abc123
myapi create-user --name "John" --email "john@test.com"
```

**MCP server (for Claude Desktop / Cursor):**

```bash
cd dist/myapi_mcp && uv pip install .
myapi-mcp  # runs via stdio, Claude Desktop spawns this
```

### GitHub Authentication

```bash
export GITHUB_TOKEN=your_github_token
uv run genalphacli parse owner/private-repo -o graph.json
```

## What Gets Generated

### CLI Tool (`dist/myapi/`)

```
dist/myapi/
├── pyproject.toml          # pip-installable with entry point
├── src/myapi/
│   ├── cli.py              # Typer CLI with all commands
│   ├── client.py           # requests HTTP client with auth + errors
│   └── _graph.json         # Embedded command graph
```

**Features:**
- Path params as positional args: `myapi get-user abc123`
- Body fields as flags: `myapi create-user --name John --email j@test.com`
- Raw JSON override: `--body '{"name": "John"}'` bypasses flags
- Pretty output: `--pretty` for Rich-formatted JSON
- Env-overridable base URL: `MYAPI_BASE_URL=https://staging.api.com`
- Auth via env var: Bearer token or API key

### MCP Server (`dist/myapi_mcp/`)

```
dist/myapi_mcp/
├── pyproject.toml          # fastmcp + httpx deps, entry point
├── src/myapi_mcp/
│   ├── server.py           # FastMCP server with @mcp.tool() per route
│   ├── client.py           # async httpx client with auth
│   └── _graph.json         # Embedded command graph
```

**Features:**
- One MCP tool per API route (AI sees each as a distinct action)
- Async httpx client with connection pooling
- `ToolError` for AI-visible errors (raw exceptions masked)
- stdio transport (Claude Desktop / Cursor compatible)
- No `print()` in server (preserves JSON-RPC stream)
- Auth via env var, same pattern as CLI

**Example interaction with Claude:**

```
User: "List all users from the API"
Claude: [calls list_users tool] → "Here are 3 users: Alice, Bob, Charlie..."

User: "Create a user named Dave with email dave@test.com"
Claude: [calls create_user tool] → "Created user Dave with ID u7f2451"

User: "Delete user u3"
Claude: [calls delete_user tool] → "User u3 deleted successfully"
```

### Claude Desktop Registration

After building an MCP server, genalphacli prints a ready-to-paste config snippet and offers to auto-register:

```json
{
  "mcpServers": {
    "myapi": {
      "command": "myapi-mcp",
      "env": {
        "MYAPI_TOKEN": "${env:MYAPI_TOKEN}",
        "MYAPI_BASE_URL": "https://api.example.com"
      }
    }
  }
}
```

### Error Handling

Both CLI and MCP server handle errors gracefully:

| HTTP Status | Message |
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

| Framework | Status |
|---|---|
| FastAPI (`@app.get()`, `@router.post()`) | Supported |
| Flask (`@app.route()`, `@blueprint.route()`) | Planned |
| Django/DRF (`path()`, `@api_view()`, `ViewSet`) | Planned |
| Spring Boot (`@GetMapping`, `@PostMapping`) | Planned |

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
| Auth type (bearer/api_key) | `.env.example` + code patterns | Auto-detected |
| Base URL | `.env.example` (`BASE_URL`, `API_URL`, `PORT`) | Auto-detected |
| CLI overrides (`--base-url`, `--auth-type`) | User flags | Highest |

## Type Mapping

| Python Type | CLI Flag / MCP Param Type |
|---|---|
| `str`, `UUID`, `EmailStr`, `datetime` | `string` |
| `int` | `integer` |
| `bool` | `boolean` |
| `float`, `Decimal` | `float` |
| `list`, `List[X]`, `set`, `tuple` | `list` |
| `UploadFile` | `file` |
| Pydantic models, `dict` | `json` |

## Security

### Parser Security

- **Git hooks disabled**: `--no-checkout` + `.gitattributes` filter driver sanitization
- **No code execution**: `ast.parse()` only — never `import`, `eval`, or `exec`
- **Repo size cap**: Rejects repositories larger than 500MB
- **Remote `$ref` blocked**: OpenAPI parser uses `RESOLVE_INTERNAL` only
- **URL validation**: `urlparse()` rejects ports, userinfo, non-ASCII, fragments
- **Temp file isolation**: `~/.cache/genalphacli/` with `0700` permissions

### Generator Security

- **Jinja2 SandboxedEnvironment**: Prevents template injection from malicious graph.json
- **String sanitization**: All graph values escaped before template rendering
- **AST safety walk**: Rejects `eval`, `exec`, `os.system`, `subprocess.run` in generated code
- **`cli_name` validation**: Must match `^[a-z][a-z0-9_]*$`
- **`base_url` validation**: Rejects private/loopback IPs and `file://` scheme
- **Token CRLF prevention**: Generated clients reject tokens with `\r\n\0`

### MCP Server Security

- **`ToolError` wrapping**: Raw exceptions never reach the AI — only intentional error messages
- **No `print()`**: Generated server never uses print (corrupts stdio JSON-RPC stream)
- **Response truncation**: API responses capped to prevent context window flooding
- **Token isolation**: Auth tokens never included in tool return values

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
| `build <graph.json>` | Generate CLI and/or MCP server from a command graph |

### Build Options

| Flag | Description |
|---|---|
| `--name`, `-n` | CLI/server name (required) |
| `--base-url` | API base URL (required) |
| `--type` | `cli`, `mcp`, or both (repeatable). Interactive prompt if omitted. |
| `--output-dir`, `-d` | Output directory (default: `dist`) |
| `--auth-type` | `bearer`, `api_key`, `none` |
| `--auth-env-var` | Env var name for auth token |

### Parse Options

| Flag | Description |
|---|---|
| `--output`, `-o` | Write JSON to a file |
| `--base-url` | API base URL override |
| `--auth-type` | Auth type override |
| `--verbose`, `-v` | Show progress and statistics |

## Project Structure

```
src/genalphacli/
  cli.py                    # Typer CLI (parse, build, detect)
  config.py                 # Environment variable management
  config_detector.py        # Auto-detect base_url and auth
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
    pip_generator.py        # CLI package generator
    mcp_generator.py        # MCP server package generator
    templates/
      pip_package/          # CLI templates (cli.py, client.py, pyproject.toml)
      mcp_package/          # MCP templates (server.py, client.py, pyproject.toml)
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
uv run pytest -v          # 93 tests, ~0.6s
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
- [x] **MCP Server Generator**: graph.json to FastMCP server for AI agents
- [x] **Live API Testing**: Mock server + end-to-end verification
- [ ] **Phase 2**: Flask and Django/DRF support
- [ ] **Phase 3**: Java (Spring Boot) support via tree-sitter
- [ ] **Streamable HTTP transport**: Remote MCP server support
- [ ] **PyPI publishing**: `uv tool install genalphacli`

## License

MIT
