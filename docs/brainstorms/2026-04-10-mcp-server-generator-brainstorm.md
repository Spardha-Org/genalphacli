# MCP Server Generator Brainstorm

**Date:** 2026-04-10
**Status:** Decided

## What We're Building

An MCP server generator that takes a command graph JSON and produces an installable MCP server. When registered with Claude Desktop or Cursor, an AI agent can call every API endpoint as a tool — "list all users", "create a project", "delete user abc123" — and get real responses.

## The Full User Flow

```
Step 1: Parse (existing)
  $ genalphacli parse owner/repo -o graph.json

Step 2: Build (multi-select)
  $ genalphacli build graph.json -n myapi --base-url https://api.example.com

  ? What would you like to generate? (space to select)
    [x] CLI tool
    [x] MCP server

  ✓ Generated CLI at: dist/myapi/
  ✓ Generated MCP server at: dist/myapi_mcp/

  Add to claude_desktop_config.json:
    {"mcpServers": {"myapi": {"command": "myapi-mcp"}}}

  ? Auto-register with Claude Desktop? [Y/n]
  ✓ Registered in claude_desktop_config.json

Step 3: Use with Claude
  User: "List all users from the API"
  Claude: [calls list_users tool] → "Here are 3 users: Alice, Bob, Charlie..."
```

## Key Decisions

1. **Jinja2 code generation** — generate server.py with `@mcp.tool()` per route using templates. Same proven pattern as CLI generator. Produces readable, modifiable code.
2. **`fastmcp` standalone SDK** — `pip install fastmcp`. More actively maintained than vendored version, clean decorator API, recommended for new servers.
3. **`httpx` async HTTP client** — FastMCP is async-native. httpx.AsyncClient is the MCP standard. CLI keeps requests, MCP gets httpx.
4. **stdio transport for v1** — Claude Desktop spawns the process. No network complexity. Streamable HTTP as future option (SSE is deprecated).
5. **One MCP tool per API route** — `list_users(limit, offset)`, `get_user(user_id)`. AI sees each as a distinct callable action.
6. **Multi-select build** — `genalphacli build` prompts with checkboxes: CLI, MCP server, or both. `--type` flag for scripting.
7. **Auto-register with Claude Desktop** — detect config file, offer to add server entry. Always print JSON snippet too.
8. **Auth via env var** — same pattern as CLI. Server reads token from env, injects into API calls.

## What Gets Generated

### MCP Server Package (`dist/myapi_mcp/`)

```
dist/myapi_mcp/
├── pyproject.toml              # fastmcp + httpx deps, entry point
├── src/myapi_mcp/
│   ├── __init__.py
│   ├── server.py               # FastMCP server with @mcp.tool() per route
│   ├── client.py               # httpx async HTTP client with auth
│   └── _graph.json             # embedded command graph
```

### Generated server.py (conceptual)

```python
from fastmcp import FastMCP
from myapi_mcp.client import api_call

mcp = FastMCP("myapi")

@mcp.tool()
async def list_users(limit: int = 10, offset: int = 0) -> str:
    """List all users. GET /api/v1/users"""
    result = await api_call("GET", "/api/v1/users", params={"limit": limit, "offset": offset})
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_user(user_id: str) -> str:
    """Get a user by ID. GET /api/v1/users/{user_id}"""
    result = await api_call("GET", f"/api/v1/users/{user_id}")
    return json.dumps(result, indent=2)

@mcp.tool()
async def create_user(name: str, email: str) -> str:
    """Create a new user. POST /api/v1/users"""
    result = await api_call("POST", "/api/v1/users", json_data={"name": name, "email": email})
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    mcp.run()  # stdio transport
```

### Generated client.py (async, httpx)

```python
import httpx, os, json

BASE_URL = os.environ.get("MYAPI_BASE_URL", "https://api.example.com")
AUTH_ENV_VAR = "MYAPI_TOKEN"

async def api_call(method, path, params=None, json_data=None) -> dict:
    headers = {}
    token = os.environ.get(AUTH_ENV_VAR, "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        response = await client.request(method, path, params=params, json=json_data, headers=headers)
        response.raise_for_status()
        return response.json()
```

## MCP Tool Mapping

| Route | MCP Tool | Parameters |
|---|---|---|
| `GET /api/v1/users` | `list_users(limit, offset)` | Query params as tool args |
| `GET /api/v1/users/{user_id}` | `get_user(user_id)` | Path param as required arg |
| `POST /api/v1/users` | `create_user(name, email)` | Body fields as args |
| `DELETE /api/v1/users/{user_id}` | `delete_user(user_id)` | Path param |

### Tool Return Values

- Success → return JSON response as string (AI reads and interprets it)
- Error → return formatted error message (AI explains to user)
- Never `print()` in stdio mode — corrupts JSON-RPC stream

## Reuse from CLI Generator

- `BuildConfig` model — same validation (cli_name, base_url, auth)
- `_sanitize()`, `_validate_generated_code()` — same security helpers
- Jinja2 `SandboxedEnvironment` — same template engine
- Template context building — same graph-to-context logic

## New Code Needed

- `generators/mcp_generator.py` — generate function for MCP packages
- `generators/templates/mcp_package/server.py.j2` — MCP server template
- `generators/templates/mcp_package/client.py.j2` — async httpx client template
- `generators/templates/mcp_package/pyproject.toml.j2` — with fastmcp dep
- Update `cli.py` build command — multi-select prompt, auto-register logic

## Constraints

- **`fastmcp` required** — generated server depends on `pip install fastmcp`
- **`httpx` required** — async HTTP client for MCP servers
- **stdio only for v1** — Streamable HTTP is future scope
- **Never print() in generated server** — use logging or stderr only
- **Same security model** — SandboxedEnvironment, string sanitization, AST walk

## Open Questions

None — all resolved.
