# CLI Generator

The `build` command with `--type cli` generates a complete, pip-installable CLI tool from a command graph JSON.

## What Gets Generated

```
dist/myapi/
├── pyproject.toml          # pip-installable with entry point
├── src/myapi/
│   ├── __init__.py
│   ├── cli.py              # Typer CLI with all commands
│   ├── client.py           # requests HTTP client with auth + errors
│   └── _graph.json         # Embedded command graph
```

## Generated CLI Features

### Path Params as Positional Args

```bash
myapi get-user abc123          # not --user-id abc123
myapi delete-user abc123
myapi get-project p1
```

### Body Fields as Flags

```bash
myapi create-user --name "John" --email "john@test.com"
myapi create-project --name "Alpha" --owner-id u1
```

### Raw JSON Override

`--body` bypasses individual flags and sends raw JSON:

```bash
myapi create-user --body '{"name": "John", "email": "john@test.com", "role": "admin"}'
```

### Pretty Output

```bash
myapi list-users --pretty      # Rich-formatted JSON
myapi list-users               # Raw JSON (pipeable to jq)
```

### Env-Overridable Base URL

```bash
export MYAPI_BASE_URL=https://staging.api.com
myapi list-users               # Hits staging instead of default
```

## Error Handling

| HTTP Status | CLI Message |
|---|---|
| 401 | `Authentication failed. Set MYAPI_TOKEN environment variable.` |
| 403 | `Permission denied.` |
| 404 | `Resource not found.` |
| 422 | `Validation error: {details}` |
| 429 | `Rate limited. Try again later.` |
| 5xx | `API error {status}: {body}` |

## Dependencies

Generated CLI packages depend on:
- `typer>=0.9.0`
- `rich>=13.0.0`
- `requests>=2.31.0`
