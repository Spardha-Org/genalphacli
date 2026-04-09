# GenAlpha CLI

Convert any API repository into a structured CLI command graph — automatically.

GenAlpha CLI clones a GitHub repository, detects the API framework, extracts all routes via static analysis, and outputs a JSON command graph that maps every endpoint to a CLI command with typed flags and parameters.

## How It Works

```
GitHub URL ──> Clone ──> Detect Framework ──> Parse Routes ──> Command Graph JSON
                              │                     │
                              │              ┌──────┴──────┐
                              │              │             │
                         FastAPI?        Layer 1       Layer 2
                         Flask?       OpenAPI Spec   AST Parsing
                         Django?      (if present)   (decorators,
                         Spring?                      type hints)
                              │              │             │
                              │              └──────┬──────┘
                              │                     │
                              │              Merge Routes
                              │            (later layer wins)
                              │                     │
                              └─────────────> Command Graph JSON
```

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Git

### Installation

```bash
git clone https://github.com/your-username/genalphacli.git
cd genalphacli
uv sync
```

### Usage

**Parse a local repository:**

```bash
uv run genalphacli parse-local /path/to/your/fastapi/project
```

**Parse from GitHub:**

```bash
uv run genalphacli parse owner/repo
```

**Save output to a file:**

```bash
uv run genalphacli parse-local ./my-api --output graph.json
```

**Detect framework only:**

```bash
uv run genalphacli detect owner/repo
```

**Verbose mode (shows progress and stats):**

```bash
uv run genalphacli parse-local ./my-api -v
```

### GitHub Authentication

For private repositories or to avoid API rate limits (60 req/hr unauthenticated):

```bash
export GITHUB_TOKEN=your_github_token
uv run genalphacli parse owner/private-repo
```

## Example Output

Given a FastAPI application with user and item endpoints:

```bash
uv run genalphacli parse-local ./my-fastapi-app
```

Produces:

```json
{
  "schema_version": "1.0.0",
  "command": "my-fastapi-app",
  "version": "0.1.0",
  "base_url": "",
  "auth": { "type": "none", "env_var": "" },
  "subcommands": [
    {
      "name": "list-users",
      "description": "List all users.",
      "method": "GET",
      "endpoint": "/users",
      "params": [
        { "name": "limit", "flag": "--limit", "type": "integer", "required": false },
        { "name": "offset", "flag": "--offset", "type": "integer", "required": false }
      ]
    },
    {
      "name": "get-user",
      "description": "Get a user by ID.",
      "method": "GET",
      "endpoint": "/users/{user_id}",
      "params": [
        { "name": "user_id", "flag": "--user-id", "type": "string", "required": true }
      ]
    },
    {
      "name": "create-user",
      "description": "Create a new user.",
      "method": "POST",
      "endpoint": "/users",
      "params": [
        { "name": "name", "flag": "--name", "type": "string", "required": true },
        { "name": "email", "flag": "--email", "type": "string", "required": true }
      ]
    }
  ],
  "metadata": {
    "total_routes": 3,
    "layer_counts": { "AST": 3 },
    "files_scanned": 12,
    "parse_time_ms": 8
  }
}
```

## Parsing Pipeline

GenAlpha CLI uses a layered parsing strategy. Each layer fills gaps the previous one missed.

### Layer 1: OpenAPI Spec Detection

Scans for `openapi.json`, `swagger.yaml`, and similar files in the repo root and common directories (`/docs`, `/api-docs`, `/specs`). If a valid spec is found, it is parsed directly — this is the fastest and most accurate path.

- Supports OpenAPI v3 and Swagger v2
- Resolves internal `$ref` references (remote URLs blocked for security)
- Falls back gracefully if the spec is malformed

### Layer 2: AST-Based Route Extraction

For repos without an OpenAPI spec, the parser uses Python's `ast` module to analyze source code and extract route information from decorators and type annotations.

**Currently supported:**

| Framework | Decorator Patterns | Parameter Extraction |
|---|---|---|
| FastAPI | `@app.get()`, `@router.post()`, `@app.api_route()` | Type hints, path params, query params with defaults |

**Handles complex patterns:**

- `include_router(router, prefix="/api/v1")` prefix composition
- `APIRouter(prefix="/users")` router-level prefixes
- `async def` handlers
- Docstrings as command descriptions
- Constant propagation for variable paths

**Automatically filters out:**

- FastAPI dependency injection params (`Depends()`, `Annotated[X, Depends()]`)
- Common DI names (`session`, `db`, `current_user`, `request`, `response`)
- Framework internals (`Request`, `Response`, `BackgroundTasks`)

### Route Merging

When both layers produce results, they are merged using route identity `(HTTP method, normalized path)`. If both layers find the same route, the later layer (AST) wins — it has more context from the actual source code.

## Type Mapping

Parameters are automatically mapped from Python type annotations to CLI flag types:

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

GenAlpha CLI is designed to perform static analysis only — it never executes code from cloned repositories.

- **Git hooks disabled**: Clones with `--no-checkout`, sanitizes `.gitattributes` filter drivers, then checks out
- **No code execution**: Uses `ast.parse()` only — never `import`, `eval`, or `exec`
- **Repo size cap**: Rejects repositories larger than 500MB
- **Remote `$ref` blocked**: OpenAPI parser only resolves internal references
- **URL validation**: Strict validation via `urlparse()` — rejects ports, userinfo, non-ASCII characters
- **Temp file isolation**: Clone directories under `~/.cache/genalphacli/` with `0700` permissions

## CLI Reference

```
genalphacli [COMMAND] [OPTIONS]
```

| Command | Description |
|---|---|
| `parse <github-url>` | Clone a GitHub repo, parse it, and output the command graph |
| `parse-local <path>` | Parse a local directory |
| `detect <github-url>` | Clone a GitHub repo and detect the framework |

### Options

| Flag | Description |
|---|---|
| `--output`, `-o` | Write JSON output to a file instead of stdout |
| `--verbose`, `-v` | Show progress details and statistics |
| `--help` | Show help for any command |

## Project Structure

```
src/genalphacli/
  cli.py              # Typer CLI entry point
  config.py           # Environment variable management
  github.py           # GitHub API, secure clone, framework detection
  models.py           # Pydantic data models, enums, type mapping
  pipeline.py         # Pipeline orchestrator, route merger, graph builder
  parsers/
    __init__.py       # FrameworkParser protocol + registry
    openapi_parser.py # Layer 1: OpenAPI/Swagger spec parsing
    fastapi_parser.py # Layer 2: FastAPI AST-based extraction
```

## Development

### Setup

```bash
git clone https://github.com/your-username/genalphacli.git
cd genalphacli
uv sync --group dev
```

### Run Tests

```bash
uv run pytest -v
```

### Lint and Format

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

### Run a Specific Test

```bash
uv run pytest tests/parsers/test_fastapi_parser.py -v
```

## Roadmap

- [ ] **Phase 2**: Flask and Django/DRF support
- [ ] **Phase 3**: Java (Spring Boot) support via tree-sitter
- [ ] **Phase 4**: LLM fallback for edge cases (opt-in)
- [ ] **Thin Client**: Execute CLI commands as actual API calls
- [ ] **Auth Support**: Bearer token, API key configuration
- [ ] **MCP Integration**: Expose as an MCP tool for AI agents

## License

MIT
