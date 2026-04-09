# MCP Server Generator

The `build` command with `--type mcp` generates a FastMCP server where every API route becomes an MCP tool. AI agents like Claude Desktop and Cursor can call your API through natural language.

## What Gets Generated

```
dist/myapi_mcp/
├── pyproject.toml          # fastmcp + httpx deps, entry point
├── src/myapi_mcp/
│   ├── server.py           # FastMCP server with @mcp.tool() per route
│   ├── client.py           # async httpx client with auth
│   └── _graph.json         # Embedded command graph
```

## How It Works

Each API route becomes an MCP tool:

| Route | MCP Tool | Parameters |
|---|---|---|
| `GET /api/v1/users` | `list_users(limit, offset)` | Query params as args |
| `GET /api/v1/users/{user_id}` | `get_user(user_id)` | Path param as required arg |
| `POST /api/v1/users` | `create_user(name, email)` | Body fields as args |
| `DELETE /api/v1/users/{user_id}` | `delete_user(user_id)` | Path param |

## Example AI Conversation

```
User: "List all users from the API"
Claude: [calls list_users tool] → "Here are 3 users: Alice, Bob, Charlie..."

User: "Create a user named Dave with email dave@test.com"
Claude: [calls create_user tool] → "Created user Dave with ID u7f2451"

User: "Delete user u3"
Claude: [calls delete_user tool] → "User u3 deleted successfully"
```

## Setup with Claude Desktop

### 1. Build the MCP server

```bash
uv run genalphacli build graph.json -n myapi --base-url https://api.com --type mcp
```

### 2. Config is printed automatically

The build command prints a ready-to-paste config snippet and offers to auto-register:

```json
{
  "mcpServers": {
    "myapi": {
      "command": "/path/to/uv",
      "args": ["--directory", "/path/to/dist/myapi_mcp", "run", "myapi-mcp"],
      "env": {
        "MYAPI_TOKEN": "${env:MYAPI_TOKEN}",
        "MYAPI_BASE_URL": "https://api.com"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

Fully quit (Cmd+Q on macOS) and reopen. The MCP tools will appear.

### 4. Make sure your API is running

The MCP server is a thin client — it forwards calls to your actual API. Your API server must be running for the tools to work.

## Config File Locations

| Client | Config Path |
|---|---|
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop (Windows) | `%APPDATA%/Claude/claude_desktop_config.json` |
| Claude Desktop (Linux) | `~/.config/claude/claude_desktop_config.json` |
| Cursor | `~/.cursor/mcp.json` |
| VS Code | `.vscode/mcp.json` |

## Transport

Currently supports **stdio** transport only (Claude Desktop spawns the process). Streamable HTTP for remote deployment is planned.

## Dependencies

Generated MCP server packages depend on:
- `fastmcp>=2.0`
- `httpx>=0.27`
