# Getting Started

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Git

## Installation

```bash
git clone https://github.com/NandishNaik01/genalphacli.git
cd genalphacli
uv sync
```

## Quick Walkthrough

### 1. Parse a Repository

```bash
# From GitHub
uv run genalphacli parse owner/repo -o graph.json

# From a local directory
uv run genalphacli parse-local ./my-fastapi-app -o graph.json

# Detect framework only
uv run genalphacli detect owner/repo
```

### 2. Build Tools

```bash
# Interactive — prompts for CLI, MCP, or both
uv run genalphacli build graph.json \
  --name myapi \
  --base-url https://api.example.com

# Explicit — build both CLI and MCP server
uv run genalphacli build graph.json \
  --name myapi \
  --base-url https://api.example.com \
  --type cli --type mcp
```

### 3. Install and Use

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
# Auto-registered with Claude Desktop during build
# Restart Claude Desktop, then talk to your API through AI
```

## GitHub Authentication

For private repositories or to avoid API rate limits (60 req/hr unauthenticated):

```bash
export GITHUB_TOKEN=your_github_token
uv run genalphacli parse owner/private-repo -o graph.json
```

## Auth Configuration

GenAlpha auto-detects auth type from `.env.example` files and code patterns. Override with flags:

```bash
uv run genalphacli build graph.json \
  --name myapi \
  --base-url https://api.example.com \
  --auth-type bearer \
  --auth-env-var MYAPI_TOKEN
```

The generated tools read the token from the env var at runtime:

```bash
export MYAPI_TOKEN=your_api_token
myapi list-users  # Bearer token injected automatically
```

## Next Steps

- [CLI Reference](cli-reference.md) — all commands and options
- [Parsing Pipeline](parsing-pipeline.md) — how route extraction works
- [MCP Server Generator](mcp-server-generator.md) — set up with Claude Desktop
