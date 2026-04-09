# CLI Reference

```
genalphacli [COMMAND] [OPTIONS]
```

## Commands

### `parse`

Clone a GitHub repo, parse it, and output a command graph JSON.

```bash
genalphacli parse <github-url> [OPTIONS]
```

| Flag | Description |
|---|---|
| `--output`, `-o` | Write JSON to a file |
| `--base-url` | API base URL override |
| `--auth-type` | `bearer`, `api_key`, `none` |
| `--auth-env-var` | Env var name for auth token |
| `--verbose`, `-v` | Show progress and statistics |

**Examples:**

```bash
genalphacli parse tiangolo/fastapi -o graph.json
genalphacli parse https://github.com/owner/repo -o graph.json -v
```

### `parse-local`

Parse a local directory.

```bash
genalphacli parse-local <path> [OPTIONS]
```

Same options as `parse`.

**Examples:**

```bash
genalphacli parse-local ./my-api -o graph.json
genalphacli parse-local repos/sai-life-sciences -o graph.json --base-url https://api.sai.com
```

### `detect`

Detect the API framework used in a repository.

```bash
genalphacli detect <github-url>
```

**Example:**

```bash
genalphacli detect tiangolo/full-stack-fastapi-template
# Output: Framework: fastapi
```

### `build`

Generate CLI and/or MCP server from a command graph JSON.

```bash
genalphacli build <graph.json> [OPTIONS]
```

| Flag | Description |
|---|---|
| `--name`, `-n` | CLI/server name (required) |
| `--base-url` | API base URL (required) |
| `--type` | `cli`, `mcp`, or both (repeatable). Interactive prompt if omitted. |
| `--output-dir`, `-d` | Output directory (default: `dist`) |
| `--auth-type` | `bearer`, `api_key`, `none` |
| `--auth-env-var` | Env var name for auth token |

**Examples:**

```bash
# Interactive — prompts for type
genalphacli build graph.json -n myapi --base-url https://api.com

# CLI only
genalphacli build graph.json -n myapi --base-url https://api.com --type cli

# MCP server only
genalphacli build graph.json -n myapi --base-url https://api.com --type mcp

# Both
genalphacli build graph.json -n myapi --base-url https://api.com --type cli --type mcp
```
