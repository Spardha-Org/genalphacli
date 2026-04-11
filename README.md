# GenAlpha CLI

**Author:** Nandish Naik

Convert any API repository into a working CLI tool and MCP server — automatically.

Parse a GitHub repo, extract all API routes via static analysis, and generate installable tools. Build a CLI for your terminal or an MCP server for AI agents like Claude and Cursor.

## How It Works

```
  PARSE                              BUILD                           USE
┌─────────────────────┐    ┌────────────────────────┐     ┌────────────────────┐
│ Clone + Detect      │    │  ? Generate:           │     │  CLI               │
│ OpenAPI Spec Parse  │───>│    [x] CLI tool        │────>│    myapi list-users │
│ AST Route Extract   │    │    [x] MCP server      │     │  MCP               │
└─────────────────────┘    └────────────────────────┘     │    "list all users" │
                                                          └────────────────────┘
```

## Quick Start

```bash
# Install
git clone https://github.com/NandishNaik01/genalphacli.git && cd genalphacli && uv sync

# Parse
uv run genalphacli parse-local ./my-fastapi-app -o graph.json

# Build (interactive — choose CLI, MCP, or both)
uv run genalphacli build graph.json -n myapi --base-url https://api.example.com

# Use the CLI
cd dist/myapi && uv pip install . && myapi --help

# Use the MCP server (Claude Desktop auto-registered during build)
# Restart Claude Desktop → "list all users from the API"
```

## Features

- **Two-layer parsing**: OpenAPI spec detection + Python AST extraction
- **FastAPI support**: decorators, `include_router` prefix resolution, Pydantic model schemas
- **CLI generator**: Typer CLI with positional path params, body flags, `--pretty`, `--body` override
- **MCP server generator**: FastMCP with `@mcp.tool()` per route, async httpx, Claude Desktop auto-register
- **Auto-detection**: auth type, base URL from `.env.example` and code patterns
- **Security**: SandboxedEnvironment, AST safety walk, no code execution, SSRF prevention

## Test Results

| Repository | Routes | Time |
|---|---|---|
| `tiangolo/full-stack-fastapi-template` | 23 | 39ms |
| `sai-life-sciences` (17 endpoints, 6 files) | 17/17 | 35ms |
| Mock server (live API calls) | 10/10 | - |

## Documentation

| Guide | |
|---|---|
| [Getting Started](docs/guide/getting-started.md) | Installation, first parse, first build |
| [CLI Reference](docs/guide/cli-reference.md) | All commands and flags |
| [Parsing Pipeline](docs/guide/parsing-pipeline.md) | How route extraction works |
| [CLI Generator](docs/guide/cli-generator.md) | Generated CLI features |
| [MCP Server Generator](docs/guide/mcp-server-generator.md) | Claude Desktop / Cursor setup |
| [Security](docs/guide/security.md) | Parser + generator + MCP security |
| [Development](docs/guide/development.md) | Dev setup, testing, project structure |

## Roadmap

- [x] FastAPI + OpenAPI parser pipeline
- [x] CLI generator (graph.json → pip package)
- [x] MCP server generator (graph.json → FastMCP server)
- [x] Live API testing with mock server
- [ ] Flask and Django/DRF support
- [ ] Java (Spring Boot) via tree-sitter
- [ ] Streamable HTTP transport for remote MCP
- [ ] PyPI publishing

## License

MIT
