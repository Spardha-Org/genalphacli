# CLI Generator Brainstorm

**Date:** 2026-04-09
**Status:** Decided

## What We're Building

A CLI factory — `genalphacli build` takes a command graph JSON and generates a standalone, installable CLI tool that makes real API calls. The generated CLI is a complete Python package that users install once and invoke from anywhere.

## The Full User Flow

```
Step 1: Parse (existing)
  $ genalphacli parse owner/repo -o graph.json
  ✓ 17 routes found

Step 2: Build (new — interactive)
  $ genalphacli build graph.json

  ? CLI name: myapi
  ? Base URL: https://api.example.com
  ? Auth type: bearer (auto-detected)
  ? Auth env var: MYAPI_TOKEN

  ? Distribution method:
    > pip package (full deps: typer + requests + rich)
      Standalone script (zero deps, stdlib only)

  ✓ Generated: dist/myapi/

Step 3: Install
  $ cd dist/myapi && pip install .
  — OR —
  $ python dist/myapi.py (standalone mode)

Step 4: Use from anywhere
  $ myapi list-users --limit 5
  → GET https://api.example.com/api/v1/users?limit=5
  → { "users": [...] }
```

## Why This Approach

GenAlpha CLI becomes a two-stage tool:
1. **Parser** (what we built) — understands API repos
2. **Generator** (what we're building) — produces standalone tools

This is more valuable than just a thin client because:
- Generated CLIs are self-contained — no dependency on genalphacli at runtime
- Users can publish their generated CLIs to PyPI for their team
- Each generated CLI is tailored to its API — proper command names, typed flags, auth
- Distribution is flexible — pip package, single script, or Docker

## Key Decisions

1. **Interactive build flow** — prompt for CLI name, base URL, auth, distribution method
2. **Two distribution methods for v1** — pip package (full deps) and standalone script (zero deps)
3. **Response display** — raw JSON by default (pipeable), `--pretty` flag for Rich-formatted output
4. **Error handling** — friendly messages by default, `--raw-errors` flag for raw API response
5. **Path params are positional** — `myapi get-user abc123`, not `--user-id abc123`
6. **Request bodies** — individual flags for known schema fields + `--body` for raw JSON override. `--body` wins if both provided.
7. **Dependency profile per distribution** — pip package gets typer+requests+rich, standalone uses stdlib only
8. **Manual rebuild only** — no auto-update in v1, user re-runs parse + build when API changes
9. **CLI only for v1** — MCP server and SDK client are future scope, not shown in menu

## What Gets Generated

### Pip Package (`dist/myapi/`)

```
dist/myapi/
├── pyproject.toml          # installable via pip/uv
├── src/myapi/
│   ├── __init__.py
│   ├── cli.py              # Typer CLI with all commands
│   ├── client.py           # HTTP client with auth, error handling
│   └── graph.json          # embedded command graph
└── README.md               # auto-generated usage docs
```

### Standalone Script (`dist/myapi.py`)

```
dist/myapi.py               # single file, zero deps, argparse + urllib
```

## Generated CLI Behavior

### Commands
- Each subcommand in graph.json becomes a CLI command
- **Path params** (`{user_id}`) → **positional arguments** (e.g., `myapi get-user abc123`)
- **Query params** → optional flags (e.g., `--limit 5`, `--offset 0`)
- **Body fields** (POST/PUT/PATCH) → individual flags from schema (e.g., `--name John --email j@t.com`)
- **Raw body override** → `--body '{"key": "value"}'` bypasses individual flags entirely
- **Conflict rule**: if `--body` is provided, individual body flags are ignored

### Auth
- Reads token from env var (e.g., `MYAPI_TOKEN`)
- Sends as Bearer header or API key header based on auth config
- Friendly error if env var not set and endpoint requires auth

### Output
- Raw JSON to stdout by default
- `--pretty` flag: Rich-formatted tables/colored JSON
- `--raw-errors` flag: show raw API error responses instead of friendly messages

### Error Handling
- 401 → "Authentication failed. Set MYAPI_TOKEN environment variable."
- 403 → "Permission denied for this endpoint."
- 404 → "Resource not found."
- 422 → "Validation error: {details from response}"
- 429 → "Rate limited. Retry after {seconds}."
- 500 → "Server error. Try again later."
- With `--raw-errors`: print full response body and headers

## Constraints

- **Generated CLIs are Python-only for v1** — both pip package and standalone script target Python. Other languages (Go binary, Rust) are future scope.
- **CLI only for v1** — the build command generates a CLI directly. No output type menu until MCP/SDK generators exist.

## Extensibility Architecture

The generator must be pluggable so adding MCP server or SDK client later is just a new module, not a rewrite:

```
genalphacli/generators/
  __init__.py        # Generator protocol + registry
  cli_pip.py         # Pip package CLI generator (v1)
  cli_standalone.py  # Standalone script CLI generator (v1)
  # Future:
  # mcp_server.py    # MCP server generator
  # sdk_typescript.py # TypeScript SDK generator
```

Each generator implements a `Generator` protocol:
- `generate(graph: CommandGraph, config: BuildConfig) -> Path` — produces output in dist/
- The build command dispatches to the right generator based on user selection
- Adding a new output type = new file implementing the protocol + register it

## Open Questions

None — all resolved during brainstorm.
