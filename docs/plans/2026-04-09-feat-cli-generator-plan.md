---
title: "feat: CLI Generator — graph.json to installable CLI"
type: feat
status: active
date: 2026-04-09
---

# feat: CLI Generator — graph.json to installable CLI

## Enhancement Summary

**Deepened on:** 2026-04-10
**Research agents used:** 5 (Python reviewer, Architecture strategist, Simplicity reviewer, Security sentinel, Framework docs researcher)

### Key Improvements
1. **Simplified scope** — dropped standalone script generator (YAGNI), dropped Generator protocol (if/else for 1 generator), flags-only CLI (no interactive prompts v1)
2. **Security hardened** — `SandboxedEnvironment` for Jinja2, validate `base_url` (HTTPS, no private IPs), sanitize graph.json strings, validate `cli_name` as safe Python identifier
3. **Generated code quality** — full type hints, `ApiError` exception (no `sys.exit()`), env-overridable BASE_URL, request timeouts, no manual Content-Type
4. **Template packaging** — `.j2` files bundled via hatchling, loaded with `importlib.resources`

---

## Overview

Add a `genalphacli build` command that takes a command graph JSON and generates a standalone, installable pip package CLI that makes real API calls. Users install it once and invoke from anywhere.

## Problem Statement

We can parse repos and produce graph.json, but nobody can use it. The graph.json needs to become a working CLI that calls real APIs — closing the loop from "repo → graph → working tool."

## Proposed Solution

A Jinja2 template-based code generator that reads `CommandGraph` and produces a **pip-installable Python package** with Typer CLI, requests-based HTTP client, auth handling, and friendly error messages.

**Scope for v1:** Pip package only. Standalone script and MCP server are future scope — add them when there's demand.

## Technical Approach

### Code Generation Strategy

**Jinja2 templates** with `SandboxedEnvironment`, `trim_blocks=True`, `lstrip_blocks=True` for clean Python output. Post-generation validation with `ast.parse()` + AST walk for dangerous patterns.

### Architecture

```
src/genalphacli/
  generators/
    __init__.py              # Jinja2 env factory, template loading
    pip_generator.py         # generate() function — produces pip package
    templates/
      pip_package/
        pyproject.toml.j2
        cli.py.j2
        client.py.j2
```

**No Generator protocol** — with only one generator, a direct function call is simpler. Add a protocol when a second generator ships.

**No shared.py** — context-building logic lives in `pip_generator.py`. Extract when duplication appears.

### BuildConfig Model

```python
class DistributionType(str, Enum):
    PIP = "pip"
    # Future: STANDALONE = "standalone", MCP = "mcp"

class BuildConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cli_name: str                    # validated: ^[a-z][a-z0-9_]*$
    base_url: str                    # validated: https:// only, no private IPs
    auth: AuthConfig
    distribution: DistributionType = DistributionType.PIP
```

### Research Insights: BuildConfig Validation

```python
import re
from urllib.parse import urlparse
import ipaddress

@field_validator("cli_name")
@classmethod
def validate_cli_name(cls, v: str) -> str:
    if not re.match(r"^[a-z][a-z0-9_]*$", v):
        raise ValueError("cli_name must be a valid Python identifier (lowercase, no dashes)")
    return v

@field_validator("base_url")
@classmethod
def validate_base_url(cls, v: str) -> str:
    parsed = urlparse(v)
    if parsed.scheme not in ("https", "http"):
        raise ValueError("base_url must use https:// (or http:// for local dev)")
    # Block private/loopback IPs
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback:
            raise ValueError(f"base_url cannot target private IP: {parsed.hostname}")
    except ValueError:
        pass  # hostname is a domain name, not an IP — that's fine
    return v.rstrip("/")
```

### New CLI Command

```python
@app.command()
def build(
    graph_file: Path = typer.Argument(help="Path to command graph JSON"),
    output_dir: Path = typer.Option("dist", "--output-dir", "-d"),
    cli_name: str = typer.Option(..., "--name", "-n", help="CLI command name"),
    base_url: str = typer.Option(..., "--base-url", help="API base URL"),
    auth_type: str | None = typer.Option(None, "--auth-type", help="bearer|api_key|none"),
    auth_env_var: str | None = typer.Option(None, "--auth-env-var", help="Env var for token"),
) -> None:
```

All values via flags. No interactive prompts in v1 — simpler to test and script.

## What Gets Generated

### Pip Package (`dist/{cli_name}/`)

```
dist/myapi/
├── pyproject.toml              # hatchling, [project.scripts], deps
├── src/myapi/
│   ├── __init__.py             # one-liner, no template needed
│   ├── cli.py                  # Typer app with all commands
│   ├── client.py               # HTTP client with auth + error handling
│   └── _graph.json             # embedded command graph for reference
```

### Generated cli.py

```python
"""Auto-generated CLI for My API."""

from __future__ import annotations

import json
import sys
from typing import Any

import typer

from myapi.client import ApiError, api_call

app = typer.Typer(name="myapi", help="CLI for My API")


def _output(data: Any, pretty: bool = False) -> None:
    """Format and print API response."""
    if pretty:
        from rich import print_json
        print_json(data=data)
    else:
        typer.echo(json.dumps(data, indent=2))


@app.command()
def list_users(
    limit: int = typer.Option(10, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich-formatted output"),
) -> None:
    """List all users."""
    try:
        result = api_call("GET", "/api/v1/users", params={"limit": limit, "offset": offset})
        _output(result, pretty)
    except ApiError as e:
        typer.echo(f"Error: {e.message}", err=True)
        raise typer.Exit(1)


@app.command()
def get_user(
    user_id: str = typer.Argument(help="User ID"),  # path param = positional
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    """Get a user by ID."""
    try:
        result = api_call("GET", f"/api/v1/users/{user_id}")
        _output(result, pretty)
    except ApiError as e:
        typer.echo(f"Error: {e.message}", err=True)
        raise typer.Exit(1)


@app.command()
def create_user(
    name: str = typer.Option(..., "--name", help="User name"),
    email: str = typer.Option(..., "--email", help="User email"),
    body: str | None = typer.Option(None, "--body", help="Raw JSON (overrides flags)"),
    pretty: bool = typer.Option(False, "--pretty"),
) -> None:
    """Create a new user."""
    if body:
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            typer.echo(f"Error: Invalid JSON in --body: {e}", err=True)
            raise typer.Exit(1)
    else:
        data = {"name": name, "email": email}
    try:
        result = api_call("POST", "/api/v1/users", json_data=data)
        _output(result, pretty)
    except ApiError as e:
        typer.echo(f"Error: {e.message}", err=True)
        raise typer.Exit(1)
```

### Generated client.py

```python
"""HTTP client for My API."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import requests

BASE_URL = os.environ.get("MYAPI_BASE_URL", "https://api.example.com")
AUTH_TYPE = "bearer"
AUTH_ENV_VAR = "MYAPI_TOKEN"
TIMEOUT = 30


class ApiError(Exception):
    """Raised when an API call fails."""

    def __init__(self, status_code: int, message: str, raw_body: str = "") -> None:
        self.status_code = status_code
        self.message = message
        self.raw_body = raw_body
        super().__init__(message)


def api_call(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    json_data: dict[str, Any] | None = None,
) -> Any:
    """Make an HTTP request to the API."""
    url = BASE_URL.rstrip("/") + path
    headers = _build_headers()

    response = requests.request(
        method, url, params=params, json=json_data, headers=headers,
        timeout=TIMEOUT, verify=True,
    )

    if not response.ok:
        _raise_api_error(response)

    if not response.content:
        return {}
    return response.json()


def _build_headers() -> dict[str, str]:
    """Build request headers with auth token."""
    headers: dict[str, str] = {}
    token = os.environ.get(AUTH_ENV_VAR, "")

    # Validate token (no CRLF injection)
    if token and ("\r" in token or "\n" in token or "\x00" in token):
        print(f"Error: {AUTH_ENV_VAR} contains invalid characters", file=sys.stderr)
        sys.exit(1)

    if token:
        if AUTH_TYPE == "bearer":
            headers["Authorization"] = f"Bearer {token}"
        elif AUTH_TYPE == "api_key":
            headers["X-API-Key"] = token
    return headers


def _raise_api_error(response: requests.Response) -> None:
    """Raise an ApiError with a friendly message."""
    messages = {
        401: f"Authentication failed. Set {AUTH_ENV_VAR} environment variable.",
        403: "Permission denied.",
        404: "Resource not found.",
        429: "Rate limited. Try again later.",
    }

    if response.status_code == 422:
        body = response.text[:500]
        raise ApiError(422, f"Validation error: {body}", response.text)

    message = messages.get(
        response.status_code,
        f"API error {response.status_code}: {response.text[:500]}",
    )
    raise ApiError(response.status_code, message, response.text)
```

### Research Insights: Generated Code Quality

- **No `sys.exit()` in client.py** — `ApiError` exception keeps the client testable. CLI layer catches it.
- **No manual `Content-Type`** — `requests` sets it automatically with `json=` kwarg.
- **`BASE_URL` env-overridable** — `os.environ.get("MYAPI_BASE_URL", "https://...")` for staging/dev/prod.
- **Token validation** — reject CRLF/null bytes to prevent header injection.
- **Response truncation** — error messages cap `response.text` at 500 chars.
- **Explicit `timeout=30`** — prevents indefinite hangs.
- **Explicit `verify=True`** — enforces TLS verification.

## Security Considerations

### Jinja2 Template Safety (Critical)

1. **Use `SandboxedEnvironment`** — prevents template injection from malicious graph.json field values
2. **Sanitize all graph.json strings** before passing to templates — escape triple-quotes, backslashes, Jinja2 delimiters (`{{ }}`, `{% %}`)
3. **Post-generation AST walk** — beyond `ast.parse()`, walk the AST to reject `eval`, `exec`, `os.system`, `subprocess`, `__import__` calls that aren't part of the template

### Input Validation

4. **`cli_name`** — must match `^[a-z][a-z0-9_]*$` (valid Python identifier, no path traversal)
5. **`base_url`** — must be HTTPS (or HTTP for explicit local dev), reject private/loopback IPs, reject `file://`
6. **Output path** — resolve and verify it stays within intended directory

### Generated Code Safety

7. **Token sanitization** — reject CRLF/null in env var values
8. **Request timeout** — always 30 seconds
9. **TLS verification** — always `verify=True`
10. **Error truncation** — cap error body output at 500 chars

## Template Packaging

### Research Insight: Hatchling includes git-tracked files automatically

If `.j2` files are committed to git and inside the package directory, hatchling includes them in the wheel with no extra config. Load at runtime with `importlib.resources`:

```python
from importlib.resources import files
from jinja2 import Environment, BaseLoader, select_autoescape

def _get_jinja_env() -> Environment:
    """Create Jinja2 environment for template rendering."""
    from jinja2.sandbox import SandboxedEnvironment

    templates_dir = files("genalphacli.generators") / "templates"

    return SandboxedEnvironment(
        loader=...,  # FileSystemLoader or custom loader from importlib
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
```

## Implementation Phases

### Phase 1: Foundation + Pip Generator

- [ ] Add `jinja2` to dependencies in `pyproject.toml`
- [ ] Add `BuildConfig` + `DistributionType` to `models.py` with validators
- [ ] Create `src/genalphacli/generators/__init__.py` with `_get_jinja_env()` factory
- [ ] Create Jinja2 templates:
  - `templates/pip_package/pyproject.toml.j2`
  - `templates/pip_package/cli.py.j2`
  - `templates/pip_package/client.py.j2`
- [ ] Create `generators/pip_generator.py`:
  - `generate(graph: CommandGraph, config: BuildConfig, output_dir: Path) -> Path`
  - Build template context from CommandGraph
  - Sanitize all string values from graph before rendering
  - Render templates, write `__init__.py` inline (one-liner)
  - Copy `_graph.json` into package
  - Post-generation: `ast.parse()` + AST walk for dangerous patterns
- [ ] Template logic for commands:
  - Path params → `typer.Argument()` (positional)
  - Query params → `typer.Option()` with defaults
  - Body params → `typer.Option(...)` required + `--body` raw JSON override
  - `--body` wins if both provided
  - `--pretty` flag on every command
  - `ApiError` exception handling in every command
- [ ] Add `build` command to `cli.py` (flags-only, no interactive prompts)
- [ ] Write tests:
  - Template rendering produces valid Python (`ast.parse()`)
  - Generated package structure is correct
  - BuildConfig validators reject bad inputs (invalid cli_name, private IP base_url)

### Phase 2: Integration Testing + Polish

- [ ] End-to-end test: parse fixture repo → build → install with `uv pip install` → invoke commands
- [ ] Test generated CLI actually makes HTTP requests (mock server)
- [ ] Test auth token handling (env var present/missing)
- [ ] Test `--pretty` output
- [ ] Test `--body` override
- [ ] Test error handling (401, 404, 422, 500)
- [ ] Update README.md with `build` command docs
- [ ] Commit generated brainstorm doc

## Acceptance Criteria

### Functional

- [ ] `genalphacli build graph.json -n myapi --base-url https://api.com` generates a pip package
- [ ] Generated package installs with `pip install .` and CLI is globally available
- [ ] Generated CLI makes real HTTP requests with correct method, path, params, body
- [ ] Path params are positional: `myapi get-user abc123`
- [ ] Body fields are individual flags: `myapi create-user --name John --email j@t.com`
- [ ] `--body '{"raw": "json"}'` overrides individual flags
- [ ] `--pretty` flag formats output with Rich
- [ ] `ApiError` exceptions produce friendly error messages (401/403/404/422/429/500)
- [ ] Auth token read from env var
- [ ] `BASE_URL` overridable via env var `{CLI_NAME}_BASE_URL`
- [ ] All generated code passes `ast.parse()` validation
- [ ] All generated code passes `ruff check`

### Non-Functional

- [ ] Generation time < 2 seconds
- [ ] Generated package deps: typer, requests, rich (minimal)
- [ ] Templates are readable and maintainable
- [ ] Extensible — adding standalone/MCP generator later is a new file, not a rewrite

### Security

- [ ] `cli_name` validated as safe Python identifier
- [ ] `base_url` validated (HTTPS, no private IPs)
- [ ] Jinja2 uses `SandboxedEnvironment`
- [ ] Graph.json strings sanitized before template rendering
- [ ] Generated code has request timeout (30s)
- [ ] Generated code validates token for CRLF injection
- [ ] Generated errors truncated (no sensitive data leakage)

## Dependencies & Risks

| Risk | Mitigation |
|---|---|
| Jinja2 templates produce invalid Python | `ast.parse()` + AST walk validation |
| Template injection from malicious graph.json | `SandboxedEnvironment` + string sanitization |
| SSRF via crafted base_url | Pydantic validator rejects private IPs and file:// |
| Body schema missing for POST endpoints | Fall back to `--body` raw JSON only |
| Package name conflicts on PyPI | User's responsibility |
| `.j2` files missing from installed package | Hatchling includes git-tracked files; verify in CI |

## References

- Brainstorm: `docs/brainstorms/2026-04-09-cli-generator-brainstorm.md`
- Parser pipeline plan: `docs/plans/2026-04-09-feat-layered-api-parser-pipeline-plan.md`
- Existing models: `src/genalphacli/models.py`
- Existing CLI: `src/genalphacli/cli.py`
- Jinja2 whitespace control: [jinja.palletsprojects.com](https://jinja.palletsprojects.com/en/stable/templates/)
- Hatchling build config: [hatch.pypa.io](https://hatch.pypa.io/latest/config/build/)
- Rich JSON formatting: [rich.readthedocs.io](https://rich.readthedocs.io/en/stable/json.html)
