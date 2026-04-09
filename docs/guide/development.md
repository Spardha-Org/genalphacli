# Development

## Setup

```bash
git clone https://github.com/NandishNaik01/genalphacli.git
cd genalphacli
uv sync --group dev
```

## Run Tests

```bash
uv run pytest -v          # 94 tests, ~0.6s
uv run pytest -q          # quiet mode
uv run pytest tests/test_mcp_generator.py -v   # specific file
```

## Lint and Format

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

## Run Mock Server

For live API testing:

```bash
uv run uvicorn tests.mock_server.server:app --port 9999
```

Then in another terminal:

```bash
uv run genalphacli parse-local tests/mock_server -o graph.json
uv run genalphacli build graph.json -n mockapi --base-url http://localhost:9999 --type cli
```

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

tests/
  fixtures/                 # Test repos (fastapi_simple, fastapi_complex, openapi_v3)
  mock_server/              # Live mock API for end-to-end testing
  parsers/                  # Parser-specific tests
  test_models.py
  test_github.py
  test_pipeline.py
  test_generators.py        # CLI generator tests
  test_mcp_generator.py     # MCP generator tests

docs/
  guide/                    # User + agent facing documentation
  design/                   # Brainstorms and implementation plans
```

## Real-World Test Results

| Repository | Routes Found | Parse Time |
|---|---|---|
| `tiangolo/full-stack-fastapi-template` | 23 routes | 39ms |
| `sai-life-sciences` (6 route files, nested imports) | 17/17 routes | 35ms |
| `testdrivenio/fastapi-crud-async` | 6 routes | 6ms |
| Mock server (10 endpoints, live API calls) | 10/10 passing | - |
