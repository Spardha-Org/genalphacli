---
title: "feat: CLI & MCP auth lifecycle — automatic token management"
type: feat
status: active
date: 2026-04-12
---

# feat: CLI & MCP Auth Lifecycle — Automatic Token Management

## Overview

Generated CLI tools and MCP servers will automatically handle the auth lifecycle: detect login endpoints at parse time, generate login/authenticate commands, extract tokens from responses using cascading confidence, store them in a shared config file, and reuse across both tools.

## Problem Statement

Generated CLIs require users to manually `export TOKEN=...` before any authenticated command works. There's no login flow, no token persistence, and no way for MCP servers to acquire tokens without manual env var setup. This makes the generated tools unusable for most authenticated APIs without significant manual setup.

## Proposed Solution

### Architecture

```
PARSE TIME                    GENERATE TIME                  RUNTIME
┌──────────────┐             ┌──────────────────┐           ┌─────────────────────┐
│ Score routes  │             │ If auth endpoint │           │ mycli login          │
│ for auth      │──tag──────>│ tagged, generate │──build──>│   → prompt creds     │
│ endpoint      │             │ login command    │           │   → call auth EP     │
│ (heuristic)   │             │ + auth tools     │           │   → cascade extract  │
└──────────────┘             └──────────────────┘           │   → save auth.json   │
                                                             │                     │
                                                             │ mycli list-users     │
                                                             │   → read auth.json   │
                                                             │   → attach token     │
                                                             │   → 401? → re-login  │
                                                             └─────────────────────┘
```

## Technical Approach

### Phase 1: Models & Data Structures

#### 1a. Extend `AuthConfig` in `src/genalphacli/models.py`

```python
class AuthConfig(BaseModel):
    type: AuthType = AuthType.NONE
    env_var: str = ""
    # New fields for auth lifecycle
    auth_endpoint: str = ""          # path of the login route (e.g., "/auth/login")
    auth_method: str = "POST"        # HTTP method for login
    auth_params: list[str] = []      # param names the login command needs (e.g., ["username", "password"])
    token_response_keys: list[str] = Field(default_factory=lambda: [
        "access_token", "token", "jwt", "id_token", "auth_token", "session_token"
    ])
    refresh_endpoint: str = ""       # optional refresh token endpoint
    header_name: str = ""            # custom auth header (empty = use default for type)
    header_template: str = ""        # e.g., "Token {token}" for DRF
```

#### 1b. Add `is_auth_endpoint` to `ParsedRoute`

```python
class ParsedRoute(BaseModel):
    # ... existing fields ...
    is_auth_endpoint: bool = False
    auth_score: float = 0.0          # confidence score from heuristic
```

#### 1c. Define auth.json schema

```python
class StoredAuth(BaseModel):
    """Schema for ~/.config/{cli_name}/auth.json"""
    token: str
    token_type: str = "bearer"       # "bearer" | "api_key"
    token_field_path: str = ""       # which response key the token came from
    refresh_token: str | None = None
    expires_at: str | None = None    # ISO 8601
    created_at: str                  # ISO 8601
    base_url: str = ""
```

### Phase 2: Auth Endpoint Detection

#### 2a. Parse-time heuristic in pipeline

**File:** `src/genalphacli/pipeline.py` — new function after `merge_routes()`

```python
def _score_auth_endpoint(route: ParsedRoute) -> float:
    """Score a route as a potential auth endpoint. Higher = more likely."""
    score = 0.0
    if route.method.upper() != "POST":
        return 0.0  # Must be POST

    # Param signals
    param_names = {p.name.lower() for p in route.params}
    if "password" in param_names or "passwd" in param_names:
        score += 3.0
    if "username" in param_names or "email" in param_names:
        score += 1.0

    # Response model signals
    resp = (route.response_model or "").lower()
    if any(k in resp for k in ("token", "auth", "session", "credential")):
        score += 2.0

    # Path signals (bonus, not primary)
    path = route.path.lower()
    auth_path_parts = ["login", "signin", "sign-in", "authenticate", "auth/token", "access-token", "session"]
    if any(part in path for part in auth_path_parts):
        score += 1.5

    return score
```

Tag the highest-scoring route (above a threshold of 3.0) as `is_auth_endpoint = True`.

#### 2b. OpenAPI `securitySchemes` parsing

**File:** `src/genalphacli/parsers/openapi_parser.py`

After parsing spec at line 69, extract:
```python
security_schemes = spec.get("components", {}).get("securitySchemes", {})
# Look for OAuth2 flows with tokenUrl
for name, scheme in security_schemes.items():
    if scheme.get("type") == "oauth2":
        flows = scheme.get("flows", {})
        for flow_type, flow in flows.items():
            if "tokenUrl" in flow:
                # This IS the auth endpoint — authoritative signal
                auth_endpoint = flow["tokenUrl"]
```

OpenAPI `securitySchemes` is the highest-confidence signal — if present, it overrides heuristics.

#### 2c. FastAPI DI param recovery

**File:** `src/genalphacli/parsers/fastapi_parser.py`

Currently `_DI_PARAM_NAMES` filters out `token`, `authorization`, `credentials`. For routes tagged as auth endpoints, we should NOT filter these — they're the actual login params, not DI. Add a post-processing step that re-examines filtered params for auth-tagged routes.

### Phase 3: Generator Changes

#### 3a. Extend `_build_context()` in `src/genalphacli/generators/pip_generator.py`

Add to context dict:
```python
"has_auth_lifecycle": bool(config.auth.auth_endpoint),
"auth_endpoint": config.auth.auth_endpoint,
"auth_params": config.auth.auth_params,  # ["username", "password"]
"refresh_endpoint": config.auth.refresh_endpoint,
```

#### 3b. Token resolution module (generated into package)

**New template:** `src/genalphacli/generators/templates/pip_package/auth.py.j2`

Generated as `src/{cli_name}/auth.py` inside the package:

```python
"""Token management — shared between CLI and MCP."""

import json
import os
import sys
import time
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "{{ cli_name }}"
AUTH_FILE = CONFIG_DIR / "auth.json"

# Level 1: High-confidence keys (ordered by priority)
TOKEN_KEYS = ["access_token", "token", "jwt", "id_token", "auth_token", "session_token"]

# Level 1.5: Common wrapper keys to search one level deep
WRAPPER_KEYS = ["data", "result", "response", "payload"]


def get_token() -> str:
    """Resolve token: env var → auth.json → empty."""
    # Priority 1: env var
    env_token = os.environ.get("{{ auth_env_var }}", "")
    if env_token:
        return env_token

    # Priority 2: auth.json
    stored = load_auth()
    if stored:
        return stored.get("token", "")

    return ""


def extract_token(response_data: dict) -> tuple[str, str]:
    """Extract token from login response using cascading confidence.

    Returns (token_value, field_path) or ("", "") if not found.
    """
    # Level 1: Check top-level common keys
    for key in TOKEN_KEYS:
        val = response_data.get(key)
        if val and isinstance(val, str) and len(val) > 8:
            return val, key

    # Level 1.5: Check one level deep in common wrappers
    for wrapper in WRAPPER_KEYS:
        nested = response_data.get(wrapper)
        if isinstance(nested, dict):
            for key in TOKEN_KEYS:
                val = nested.get(key)
                if val and isinstance(val, str) and len(val) > 8:
                    return val, f"{wrapper}.{key}"

    # Level 2: JWT pattern match (eyJ... with dots)
    for key, val in _flatten_strings(response_data):
        if isinstance(val, str) and val.startswith("eyJ") and val.count(".") == 2:
            return val, key

    return "", ""


def save_auth(token: str, field_path: str, token_type: str = "bearer",
              refresh_token: str | None = None, base_url: str = "") -> None:
    """Save token to auth.json with restricted permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    auth_data = {
        "token": token,
        "token_type": token_type,
        "token_field_path": field_path,
        "refresh_token": refresh_token,
        "base_url": base_url,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    tmp = AUTH_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(auth_data, indent=2))
    os.replace(str(tmp), str(AUTH_FILE))  # atomic on all platforms
    os.chmod(AUTH_FILE, 0o600)
    print(f"Token saved to {AUTH_FILE}", file=sys.stderr)


def load_auth() -> dict | None:
    """Load auth.json if it exists."""
    if AUTH_FILE.exists():
        try:
            return json.loads(AUTH_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def clear_auth() -> None:
    """Delete auth.json."""
    AUTH_FILE.unlink(missing_ok=True)


def _flatten_strings(d: dict, prefix: str = "") -> list[tuple[str, str]]:
    """Flatten dict to list of (path, value) for string values."""
    items = []
    for k, v in d.items():
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, str):
            items.append((path, v))
        elif isinstance(v, dict):
            items.extend(_flatten_strings(v, path))
    return items
```

#### 3c. Update CLI template — `cli.py.j2`

Add after the commands loop:

```python
{% if has_auth_lifecycle %}
@app.command(name="login")
def login(
    {% for param in auth_params %}
    {{ param }}: str = typer.Option(
        ..., prompt=True,
        {% if "password" in param or "secret" in param or "passwd" in param %}
        hide_input=True,
        {% endif %}
    ),
    {% endfor %}
) -> None:
    """Authenticate and store token for subsequent commands."""
    from {{ cli_name }}.auth import extract_token, save_auth
    resp = _client.{{ auth_method|lower }}("{{ auth_endpoint }}", json={
        {% for param in auth_params %}
        "{{ param }}": {{ param }},
        {% endfor %}
    })
    token, field_path = extract_token(resp)
    if not token:
        # Level 3: Ask user
        typer.echo("Could not auto-detect token. Response keys:")
        for i, (k, v) in enumerate(_flat_strings(resp)):
            typer.echo(f"  [{i}] {k}: {v[:40]}...")
        choice = typer.prompt("Which field is the token? (number)")
        items = list(_flat_strings(resp))
        token, field_path = items[int(choice)]
    save_auth(token, field_path, token_type="{{ auth_type }}")
    typer.echo("Logged in successfully.")


@app.command(name="logout")
def logout() -> None:
    """Clear stored authentication token."""
    from {{ cli_name }}.auth import clear_auth
    clear_auth()
    typer.echo("Logged out. Token removed.")


@app.command(name="auth-status")
def auth_status() -> None:
    """Show current authentication status."""
    from {{ cli_name }}.auth import load_auth, AUTH_FILE
    import os
    env_token = os.environ.get("{{ auth_env_var }}", "")
    stored = load_auth()
    if env_token:
        typer.echo(f"Authenticated via env var {{ auth_env_var }} (length: {len(env_token)})")
    elif stored:
        typer.echo(f"Authenticated via {AUTH_FILE}")
        typer.echo(f"  Token field: {stored.get('token_field_path', '?')}")
        typer.echo(f"  Stored at:   {stored.get('created_at', '?')}")
    else:
        typer.echo("Not authenticated. Run: {{ cli_name }} login")
{% endif %}
```

#### 3d. Update client template — `client.py.j2`

Replace `_build_headers()` token resolution:

```python
def _build_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    {% if has_auth_lifecycle %}
    from {{ cli_name }}.auth import get_token
    token = get_token()
    {% else %}
    token = os.environ.get(AUTH_ENV_VAR, "")
    {% endif %}
    if token:
        _validate_token(token)
        if AUTH_TYPE == "bearer":
            headers["Authorization"] = f"Bearer {token}"
        elif AUTH_TYPE == "api_key":
            headers["X-API-Key"] = token
    return headers
```

Update 401 error message:
```python
{% if has_auth_lifecycle %}
"Authentication failed. Run: {{ cli_name }} login"
{% else %}
f"Authentication failed. Set {AUTH_ENV_VAR} environment variable."
{% endif %}
```

#### 3e. Update MCP server template — `server.py.j2`

Add after the tools loop:

```python
{% if has_auth_lifecycle %}
@mcp.tool()
async def authenticate({% for p in auth_params %}{{ p }}: str{% if not loop.last %}, {% endif %}{% endfor %}) -> str:
    """Authenticate and store token for subsequent tool calls."""
    from {{ cli_name }}_mcp.auth import extract_token, save_auth
    result = await api_call("{{ auth_method }}", "{{ auth_endpoint }}", json_data={
        {% for p in auth_params %}"{{ p }}": {{ p }},{% endfor %}
    })
    token, field_path = extract_token(result)
    if not token:
        return json.dumps({"error": "Could not extract token", "response": result})
    save_auth(token, field_path, token_type="{{ auth_type }}")
    return json.dumps({"status": "authenticated", "token_field": field_path})


@mcp.tool()
async def refresh_auth() -> str:
    """Re-authenticate using stored credentials or refresh token."""
    from {{ cli_name }}_mcp.auth import load_auth, clear_auth
    stored = load_auth()
    if not stored:
        return json.dumps({"error": "No stored auth. Call authenticate first."})
    {% if refresh_endpoint %}
    refresh_token = stored.get("refresh_token")
    if refresh_token:
        result = await api_call("POST", "{{ refresh_endpoint }}", json_data={"refresh_token": refresh_token})
        token, field_path = extract_token(result)
        if token:
            save_auth(token, field_path)
            return json.dumps({"status": "refreshed"})
    {% endif %}
    clear_auth()
    return json.dumps({"error": "Token expired. Call authenticate again."})
{% endif %}
```

#### 3f. Update MCP client template — `mcp_package/client.py.j2`

Same token resolution change as pip client — read from `get_token()` instead of env var only.

#### 3g. Generate `auth.py` into both packages

**File:** `src/genalphacli/generators/pip_generator.py` — add to `generate()`:

```python
if context["has_auth_lifecycle"]:
    auth_template = env.get_template("pip_package/auth.py.j2")
    auth_code = auth_template.render(context)
    (src_dir / "auth.py").write_text(auth_code)
```

Same for `mcp_generator.py`.

### Phase 4: Pipeline Integration

#### 4a. Add auth endpoint scoring step

**File:** `src/genalphacli/pipeline.py`

After `merge_routes()` (line 254), before `detect_config()`:

```python
# Score and tag auth endpoints
auth_candidates = [(r, _score_auth_endpoint(r)) for r in merged_routes]
auth_candidates.sort(key=lambda x: x[1], reverse=True)
if auth_candidates and auth_candidates[0][1] >= 3.0:
    best = auth_candidates[0][0]
    best.is_auth_endpoint = True
    logger.info("Tagged auth endpoint: %s %s (score: %.1f)", best.method, best.path, auth_candidates[0][1])
```

#### 4b. Propagate auth endpoint info into `AuthConfig`

In `routes_to_command_graph()`, find the tagged auth route and populate:

```python
auth_route = next((r for r in routes if r.is_auth_endpoint), None)
if auth_route:
    auth_config.auth_endpoint = auth_route.path
    auth_config.auth_method = auth_route.method
    auth_config.auth_params = [p.name for p in auth_route.params]
```

## File Manifest

| File | Action | Description |
|------|--------|-------------|
| `src/genalphacli/models.py` | Edit | Extend `AuthConfig`, add `is_auth_endpoint` to `ParsedRoute`, add `StoredAuth` |
| `src/genalphacli/pipeline.py` | Edit | Add `_score_auth_endpoint()`, tag best candidate, propagate to auth config |
| `src/genalphacli/parsers/openapi_parser.py` | Edit | Parse `securitySchemes` for `tokenUrl` |
| `src/genalphacli/generators/pip_generator.py` | Edit | Add auth context vars, generate `auth.py` |
| `src/genalphacli/generators/mcp_generator.py` | Edit | Generate `auth.py` into MCP package |
| `src/genalphacli/generators/templates/pip_package/auth.py.j2` | Create | Shared token management module |
| `src/genalphacli/generators/templates/pip_package/cli.py.j2` | Edit | Add `login`, `logout`, `auth-status` commands |
| `src/genalphacli/generators/templates/pip_package/client.py.j2` | Edit | Token resolution: env var → auth.json |
| `src/genalphacli/generators/templates/mcp_package/auth.py.j2` | Create | Same auth module for MCP (symlink or copy of pip version) |
| `src/genalphacli/generators/templates/mcp_package/server.py.j2` | Edit | Add `authenticate`, `refresh_auth` tools |
| `src/genalphacli/generators/templates/mcp_package/client.py.j2` | Edit | Token resolution: env var → auth.json |
| `src/genalphacli/generators/templates/pip_package/pyproject.toml.j2` | Edit | No new deps needed (all stdlib) |

## Acceptance Criteria

### Functional

- [ ] Parse-time heuristic detects login endpoint for FastAPI repos with `OAuth2PasswordBearer`
- [ ] OpenAPI parser extracts `tokenUrl` from `securitySchemes`
- [ ] Generated CLI has `login` command that prompts for credentials and stores token
- [ ] Generated CLI has `logout` and `auth-status` commands
- [ ] Token extracted using cascading confidence (common keys → nested wrappers → JWT pattern → ask user)
- [ ] Token stored in `~/.config/{cli_name}/auth.json` with 600 permissions
- [ ] All commands read token from env var (priority 1) then auth.json (priority 2)
- [ ] 401 response shows "Run {cli_name} login" hint
- [ ] MCP server has `authenticate` and `refresh_auth` tools
- [ ] MCP server reads shared auth.json (CLI login → MCP picks it up)
- [ ] Password params use `hide_input=True` in typer prompts
- [ ] Atomic file writes with `os.replace()` for cross-platform safety

### Non-Functional

- [ ] No new dependencies added to generated packages (all stdlib: json, os, pathlib, time)
- [ ] Backward compatible — CLIs generated without auth lifecycle still work via env var
- [ ] `has_auth_lifecycle` is false when no auth endpoint detected — no login command generated

## Edge Cases

| Case | Behavior |
|------|----------|
| No auth endpoint detected at parse time | No `login` command generated. Env var still works. 401 shows generic hint. |
| Token extraction fails all levels | Level 3: CLI prompts user to pick field. MCP returns error with raw response. |
| Nested token (`data.access_token`) | Level 1.5 checks one deep inside `data`, `result`, `response`, `payload` |
| API with no login endpoint (API key only) | `auth_endpoint` stays empty, no login command. User exports env var. |
| Token expires mid-session | 401 → "Run {cli_name} login" (v1: no auto-refresh on 401) |
| CLI and MCP write auth.json simultaneously | `os.replace()` is atomic. Last writer wins. Acceptable for v1. |
| Windows path | Use `Path.home() / ".config"` which works on Windows too |
| Multiple auth candidates (login + register) | Highest scoring route wins. Password param gives +3, path bonus gives +1.5 |

## Dependencies & Risks

- **No new deps** — auth.py uses only stdlib (json, os, pathlib, time)
- **Heuristic accuracy** — false positive auth endpoint means broken login command. Mitigated by score threshold (3.0) and runtime fallback.
- **OAuth2 redirect flows** — not supported in v1. Only password-grant style login.

## Research: Prior Art

**No existing tool solves this end-to-end.** Token extraction from unknown response shapes is novel.

| Pattern | Source | How we use it |
|---------|--------|---------------|
| Login endpoint path heuristics | AuthREST paper (arxiv 2509.10320, 100 APIs) | Adopt param priority: `password` > `pass`, `username` > `email` > `login` |
| `tokenUrl` from OpenAPI securitySchemes | Speakeasy, Fern | Highest-confidence signal, overrides heuristics |
| JWT regex detection | Standard | `/^eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/` as Level 2 |
| Credential chain | AWS CLI | env var → config file → prompt |
| Token expiry tolerance | Speakeasy | 5-minute clock drift buffer |
| Atomic file + keyring fallback | GitHub CLI | `os.replace()` atomic write, plaintext config with 600 perms |

## References

- Brainstorm: `docs/brainstorms/2026-04-12-cli-mcp-auth-lifecycle-brainstorm.md`
- Existing auth detection: `src/genalphacli/config_detector.py`
- CLI template: `src/genalphacli/generators/templates/pip_package/cli.py.j2`
- MCP template: `src/genalphacli/generators/templates/mcp_package/server.py.j2`
- Client template: `src/genalphacli/generators/templates/pip_package/client.py.j2`
