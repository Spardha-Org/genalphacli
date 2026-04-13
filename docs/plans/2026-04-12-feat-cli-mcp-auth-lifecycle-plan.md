---
title: "feat: CLI & MCP auth lifecycle — automatic token management"
type: feat
status: active
date: 2026-04-12
deepened: 2026-04-13
---

# feat: CLI & MCP Auth Lifecycle — Automatic Token Management

## Enhancement Summary

**Deepened on:** 2026-04-13
**Research agents used:** security-sentinel, architecture-strategist, code-simplicity-reviewer, best-practices-researcher (x3)

### Key Simplifications (from simplicity review)
1. **Dropped LLM classification** — user confirms candidates in modal anyway, heuristic filter is sufficient
2. **Dropped `refresh_auth` MCP tool** — re-call `authenticate` on 401 instead
3. **Dropped `auth-status` CLI command** — v1 ships `login` + `logout` only
4. **Flattened extraction to 2 levels** — common keys + ask user (dropped JWT regex scan)
5. **Simplified auth.json** to 2 fields: `token` + `token_field_path`
6. ~30% LOC reduction vs original plan

### Critical Security Findings (from security review)
- MCP `authenticate` tool: document that password transits through LLM context
- Pin tokens to origin — never send to redirected/changed URLs
- Make auth detection non-fatal in ParseWorkflow

---

## Overview

Generated CLI tools and MCP servers automatically handle auth: detect login endpoint candidates via heuristics on the route graph, show user a confirmation modal, then generate login/authenticate commands that extract and store tokens.

Auth detection is a **separate, framework-agnostic Temporal activity** that works on the route graph. Any future parser just produces a route graph, auth detection works automatically.

## Problem Statement

Generated CLIs require `export TOKEN=...` before any authenticated command. No login flow, no token persistence, no MCP auth support.

## Architecture

```
ParseWorkflow
  1. clone_repo_activity
  2. parse_routes_activity
  3. detect_auth_activity (NEW, non-fatal)
     → Filter POST routes with credential-like params → candidates[]
     → Store candidates in service metadata
  4. update status → "parsed"
              ↓
Frontend (service detail page)
  5. Show "Configure Auth" modal with candidates
  6. User assigns roles (login/refresh) or skips
  7. Auth config saved → merged into CommandGraph.auth
              ↓
GenerateWorkflow (enhanced)
  8. Generator reads auth config from CommandGraph.auth
  9. Generates login command, auth.py, authenticate MCP tool
              ↓
Runtime
  10. mycli login → call endpoint → extract token → save auth.json
  11. All commands: env var → auth.json → empty → 401 hint
```

## Technical Approach

### Phase 1: Auth Detection Activity (Worker)

#### 1a. Schemas

**File:** `worker/activities/schemas.py`

```python
@dataclass
class DetectAuthInput:
    route_graph: dict
    service_id: str

@dataclass
class DetectAuthOutput:
    candidates: list[dict]  # [{endpoint, method, params, response_model, description}]
    auth_type: str           # "bearer" | "api_key" | "none"
```

No `confidence` or `reasoning` fields — user assigns roles in the modal.

#### 1b. Filter step — heuristic candidate detection

**File:** `worker/activities/auth_activities.py`

```python
# Credential param names (from AuthREST paper, validated on 100 APIs)
CRED_PARAMS = {"password", "passwd", "pass", "secret", "pin", "otp", "code",
               "token", "refresh_token", "grant_type"}
IDENTITY_PARAMS = {"username", "email", "login", "user", "phone", "account"}

# Auth path segments (fallback when no credential params found)
AUTH_PATH_SEGMENTS = {"login", "signin", "sign-in", "authenticate", "auth",
                      "token", "session", "oauth", "access-token"}

def _filter_auth_candidates(route_graph: dict) -> list[dict]:
    """Filter POST routes that could be auth endpoints. Framework-agnostic."""
    candidates = []
    for cmd in route_graph.get("subcommands", []):
        if cmd["method"].upper() != "POST":
            continue
        param_names = {p["name"].lower() for p in cmd.get("params", [])}
        if param_names & CRED_PARAMS or param_names & IDENTITY_PARAMS:
            candidates.append({...})

    # Fallback: path-based detection if no param matches
    if not candidates:
        for cmd in route_graph.get("subcommands", []):
            if cmd["method"].upper() != "POST":
                continue
            path_lower = cmd["endpoint"].lower()
            if any(seg in path_lower for seg in AUTH_PATH_SEGMENTS):
                candidates.append({...})

    return candidates
```

#### 1c. Activity definition

```python
@activity.defn
def detect_auth_activity(input: DetectAuthInput) -> DetectAuthOutput:
    candidates = _filter_auth_candidates(input.route_graph)
    auth_type = input.route_graph.get("auth", {}).get("type", "none")
    return DetectAuthOutput(candidates=candidates, auth_type=auth_type)
```

No LLM call. Just filter + return.

#### 1d. Non-fatal integration into ParseWorkflow

**File:** `worker/workflows/parse_workflow.py`

```python
# Step 3: Detect auth endpoints (non-fatal)
auth_candidates = []
try:
    auth_result = await workflow.execute_activity(
        detect_auth_activity,
        DetectAuthInput(route_graph=parse_result.route_graph, service_id=input.service_id),
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=RetryPolicy(maximum_attempts=1),
    )
    auth_candidates = auth_result.candidates
except Exception:
    pass  # Auth detection failure does not fail the workflow

# Include in metadata
metadata = {
    ...existing...,
    "auth_candidates": auth_candidates,
}
```

### Phase 2: Frontend — Auth Confirmation Modal

#### 2a. Modal UI (service detail page)

After parsing completes, if `service.metadata?.auth_candidates` is non-empty, show a section/modal:

```
┌─────────────────────────────────────────────┐
│ Configure Authentication                     │
│                                              │
│ We detected these potential auth endpoints:  │
│                                              │
│ POST /login/access-token                     │
│   Params: username, password                 │
│   Role: [Login ▼]                           │
│                                              │
│ POST /auth/refresh                           │
│   Params: refresh_token                      │
│   Role: [Refresh ▼]                         │
│                                              │
│ ☐ Skip — this API uses external auth         │
│                                              │
│              [Confirm]  [Skip]               │
└─────────────────────────────────────────────┘
```

Role dropdown options: Login, Refresh, Skip (per candidate).

#### 2b. API endpoint

**File:** `services/core/routes/services.py`

```python
class AuthConfigRequest(BaseModel):
    login_endpoint: str = ""
    login_params: list[str] = []
    refresh_endpoint: str = ""
    auth_type: str = "bearer"

@router.post("/services/{service_id}/auth-config")
async def set_auth_config(service_id: str, body: AuthConfigRequest, db: DbDep):
    """Save user-confirmed auth config. Merges into route_graph.auth."""
    service = ...
    # Merge into route_graph.auth (so generators read from established path)
    route_graph = service.route_graph or {}
    route_graph.setdefault("auth", {})
    route_graph["auth"]["login_endpoint"] = body.login_endpoint
    route_graph["auth"]["login_params"] = body.login_params
    route_graph["auth"]["refresh_endpoint"] = body.refresh_endpoint
    service.route_graph = route_graph
    # Also store in metadata for UI
    metadata = service.metadata_json or {}
    metadata["auth_config"] = body.model_dump()
    service.metadata_json = metadata
    await db.commit()
    return {"ok": True}
```

### Research Insights: Merging into CommandGraph.auth

**Best Practice (from architecture review):** Flow confirmed auth config through `CommandGraph.auth`, not as a side-channel. The generators already read `graph.auth` — extend `AuthConfig` with new fields:

```python
class AuthConfig(BaseModel):
    type: AuthType = AuthType.NONE
    env_var: str = ""
    login_endpoint: str = ""
    login_params: list[str] = []
    refresh_endpoint: str = ""
```

This keeps the generator interface unchanged.

#### 2c. Frontend API + hook

```typescript
// api.ts
setAuthConfig: (serviceId: string, config: { login_endpoint: string; login_params: string[]; refresh_endpoint?: string; auth_type: string }) =>
  apiFetch<{ ok: boolean }>(`/services/${serviceId}/auth-config`, { method: "POST", body: JSON.stringify(config) }),

// hooks.ts
useSetAuthConfig()  // invalidates service query on success
```

### Phase 3: Generator Changes

#### 3a. Extend `_build_context()`

**File:** `src/genalphacli/generators/pip_generator.py`

```python
"has_auth_lifecycle": bool(config.auth.login_endpoint),
"auth_endpoint": config.auth.login_endpoint,
"auth_params": config.auth.login_params,
"refresh_endpoint": config.auth.refresh_endpoint,
```

#### 3b. New template: `auth.py.j2`

**File:** `src/genalphacli/generators/templates/pip_package/auth.py.j2`

Token management module (stdlib only):

```python
"""Token management — shared between CLI and MCP."""
import json, os, sys, time
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "{{ cli_name }}"
AUTH_FILE = CONFIG_DIR / "auth.json"

# Token field priority (from OAuth2 RFC 6749 + real API survey)
TOKEN_KEYS = [
    "access_token", "token", "jwt", "id_token", "auth_token", "session_token",
    "accessToken", "idToken", "authToken", "bearerToken",
    "access", "key",
]
# Common wrappers to search one level deep
WRAPPER_KEYS = ["data", "result", "response", "payload", "session", "auth"]

# False positives to skip
SKIP_KEYS = {"csrf_token", "csrfToken", "session_id", "request_id", "correlation_id"}

def get_token() -> str:
    """Resolve: env var → auth.json → empty."""
    env = os.environ.get("{{ auth_env_var }}", "")
    if env:
        return env
    stored = load_auth()
    return stored.get("token", "") if stored else ""

def extract_token(response: dict) -> tuple[str, str]:
    """Extract token from login response. Returns (token, field_path)."""
    # Check for token_type co-occurrence (near-100% accuracy for OAuth2)
    if "token_type" in response:
        for key in TOKEN_KEYS:
            if key in response and isinstance(response[key], str) and len(response[key]) > 8:
                return response[key], key

    # Level 1: Top-level common keys
    for key in TOKEN_KEYS:
        val = response.get(key)
        if val and isinstance(val, str) and len(val) > 8 and key not in SKIP_KEYS:
            return val, key

    # Level 1.5: One level deep in wrappers
    for wrapper in WRAPPER_KEYS:
        nested = response.get(wrapper)
        if isinstance(nested, dict):
            for key in TOKEN_KEYS:
                val = nested.get(key)
                if val and isinstance(val, str) and len(val) > 8:
                    return val, f"{wrapper}.{key}"

    return "", ""

def save_auth(token: str, field_path: str) -> None:
    """Atomic write to auth.json with 600 permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {"token": token, "token_field_path": field_path}
    tmp = AUTH_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(str(tmp), str(AUTH_FILE))
    os.chmod(AUTH_FILE, 0o600)
    print(f"Token saved to {AUTH_FILE}", file=sys.stderr)

def load_auth() -> dict | None:
    if AUTH_FILE.exists():
        try:
            return json.loads(AUTH_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None

def clear_auth() -> None:
    AUTH_FILE.unlink(missing_ok=True)
```

### Research Insights: Token Extraction

**From real API survey (12+ APIs):**
- `access_token` is used by: GitHub, Auth0, Okta, Keycloak, Google, Supabase, Microsoft Entra, FastAPI
- `token` is used by: Django REST, Laravel Sanctum, Express/Node
- `jwt` is used by: Strapi
- `access` is used by: Django SimpleJWT

**`token_type` co-occurrence signal:** If the response contains `token_type` alongside a token field, it's near-100% an OAuth2 response. Check this first.

**False positives to always reject:** `csrf_token`, `session_id`, `request_id`, `correlation_id`, UUIDs. The `SKIP_KEYS` set handles this.

#### 3c. CLI template additions — `cli.py.j2`

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
    """Authenticate and store token."""
    from {{ cli_name }}.auth import extract_token, save_auth
    import json
    resp = _client.post("{{ auth_endpoint }}", json={
        {% for param in auth_params %}"{{ param }}": {{ param }},{% endfor %}
    })
    token, field_path = extract_token(resp)
    if not token:
        # Ask user to pick the token field
        typer.echo("Could not auto-detect token. Response fields:")
        items = [(k, v) for k, v in resp.items() if isinstance(v, str)]
        for i, (k, v) in enumerate(items):
            typer.echo(f"  [{i}] {k}: {str(v)[:50]}...")
        idx = typer.prompt("Which field is the token?", type=int)
        token, field_path = items[idx][1], items[idx][0]
    save_auth(token, field_path)
    typer.echo("Logged in successfully.")

@app.command(name="logout")
def logout() -> None:
    """Clear stored token."""
    from {{ cli_name }}.auth import clear_auth
    clear_auth()
    typer.echo("Logged out.")
{% endif %}
```

### Research Insights: Security

**Password params:** Never accept password as a CLI flag (shell history exposure). Only via interactive prompt (`typer.Option(prompt=True, hide_input=True)`) or env var.

**Token origin pinning:** Before attaching token to any request, verify the request URL matches the base URL where the token was obtained. Don't follow redirects on authenticated requests.

#### 3d. MCP template additions — `server.py.j2`

```python
{% if has_auth_lifecycle %}
@mcp.tool()
async def authenticate({% for p in auth_params %}{{ p }}: str{% if not loop.last %}, {% endif %}{% endfor %}) -> str:
    """Authenticate and store token for subsequent tool calls."""
    from {{ cli_name }}_mcp.auth import extract_token, save_auth
    result = await api_call("POST", "{{ auth_endpoint }}", json_data={
        {% for p in auth_params %}"{{ p }}": {{ p }},{% endfor %}
    })
    token, field_path = extract_token(result)
    if not token:
        return json.dumps({"error": "Could not extract token from response", "response_keys": list(result.keys())})
    save_auth(token, field_path)
    return json.dumps({"status": "authenticated", "token_field": field_path})
{% endif %}
```

### Research Insights: MCP Security

**Password exposure:** The MCP protocol has no "secret" parameter type. Passwords in `authenticate` tool params are visible to the LLM. This is a known tradeoff — document it. Alternative (out-of-band browser flow) is too complex for v1.

**401 handling in MCP:** When any tool gets 401, return error telling agent to call `authenticate` first. No automatic retry.

#### 3e. Client template changes — `client.py.j2` (both pip and mcp)

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

Update 401 error:
```python
{% if has_auth_lifecycle %}
"Authentication failed. Run: {{ cli_name }} login"
{% else %}
f"Authentication failed. Set {AUTH_ENV_VAR} environment variable."
{% endif %}
```

#### 3f. Generate `auth.py` into both packages

**Files:** `pip_generator.py` and `mcp_generator.py`

```python
if context["has_auth_lifecycle"]:
    auth_template = env.get_template("pip_package/auth.py.j2")
    (src_dir / "auth.py").write_text(auth_template.render(context))
```

Both packages generate the same `auth.py` using the same `cli_name`, so they share the same `~/.config/{cli_name}/auth.json` path.

### Phase 4: Core Endpoint + Worker Registration

#### 4a. Register activity

**File:** `worker/worker.py` — add `detect_auth_activity` to activities list.

#### 4b. Frontend proxy

`web/src/app/api/services/[[...path]]/route.ts` already proxies POST — no changes needed.

## File Manifest

| File | Action | Description |
|------|--------|-------------|
| `worker/activities/schemas.py` | Edit | Add `DetectAuthInput`, `DetectAuthOutput` |
| `worker/activities/auth_activities.py` | Create | Heuristic filter for auth candidates |
| `worker/workflows/parse_workflow.py` | Edit | Add detect_auth_activity (non-fatal step 3) |
| `worker/workflows/pypi_parse_workflow.py` | Edit | Same |
| `worker/worker.py` | Edit | Register detect_auth_activity |
| `src/genalphacli/models.py` | Edit | Extend `AuthConfig` with login_endpoint, login_params, refresh_endpoint |
| `services/core/routes/services.py` | Edit | Add POST /services/{id}/auth-config |
| `web/src/app/(app)/services/[id]/page.tsx` | Edit | Auth confirmation UI after parsing |
| `web/src/data/api.ts` | Edit | Add setAuthConfig |
| `web/src/data/hooks.ts` | Edit | Add useSetAuthConfig |
| `src/genalphacli/generators/pip_generator.py` | Edit | Auth context + generate auth.py |
| `src/genalphacli/generators/mcp_generator.py` | Edit | Generate auth.py into MCP package |
| `src/genalphacli/generators/templates/pip_package/auth.py.j2` | Create | Token management module |
| `src/genalphacli/generators/templates/pip_package/cli.py.j2` | Edit | Add login/logout commands |
| `src/genalphacli/generators/templates/pip_package/client.py.j2` | Edit | Token resolution chain |
| `src/genalphacli/generators/templates/mcp_package/server.py.j2` | Edit | Add authenticate tool |
| `src/genalphacli/generators/templates/mcp_package/client.py.j2` | Edit | Token resolution chain |

## Acceptance Criteria

### Functional

- [ ] `detect_auth_activity` filters POST routes with credential-like params
- [ ] Auth candidates stored in service metadata (non-fatal — never fails ParseWorkflow)
- [ ] Frontend shows auth confirmation UI with role dropdowns
- [ ] User can confirm login/refresh endpoints or skip entirely
- [ ] Confirmed config merges into `route_graph.auth` for generators
- [ ] Generator produces `login` + `logout` commands when auth config present
- [ ] Generator produces `authenticate` MCP tool when auth config present
- [ ] Token extracted using common keys + wrapper search + user fallback
- [ ] Token stored in `~/.config/{cli_name}/auth.json` with 600 permissions
- [ ] Token resolution: env var → auth.json → empty
- [ ] 401 shows "Run {cli_name} login" hint
- [ ] Password params use `hide_input=True` in prompts
- [ ] Backward compatible — no auth config = env-var-only mode (current behavior)

### Non-Functional

- [ ] Auth detection activity completes in <5s (no LLM call)
- [ ] No new dependencies in generated packages (auth.py is stdlib only)
- [ ] Atomic file writes with `os.replace()`

## Edge Cases

| Case | Behavior |
|------|----------|
| No auth candidates found | No modal shown. Generator produces env-var-only code. |
| User clicks "Skip" | `auth_config: null`. Generator produces env-var-only code. |
| Token extraction fails both levels | CLI: prompt user to pick field. MCP: return error with response keys. |
| API with only API key (no login) | No candidates. User exports env var. |
| Multiple login-like endpoints | All shown in modal. User picks roles. |
| CLI and MCP write auth.json simultaneously | `os.replace()` is atomic. Last writer wins. |
| Future Java/Express parser | Produces route graph → auth detection works automatically. |

## Security Considerations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Plaintext token on disk | HIGH | 600 permissions. Document risk. v2: keyring support. |
| MCP authenticate exposes password to LLM | CRITICAL | Document tradeoff. v2: out-of-band browser flow. |
| Token sent to wrong host (redirect) | HIGH | Don't follow redirects on authenticated requests. |
| Shell history exposure | MEDIUM | Password only via prompt, never CLI flag. |
| False positive token extraction | MEDIUM | `SKIP_KEYS` filter + `token_type` co-occurrence check. |

## References

- Brainstorm: `docs/brainstorms/2026-04-12-cli-mcp-auth-lifecycle-brainstorm.md`
- AuthREST paper: arxiv 2509.10320 (login endpoint heuristics, 100 APIs)
- OAuth2 RFC 6749 Section 5.1 (token response format)
- AWS CLI credential chain pattern
- `gh` CLI keyring storage (github.com/cli/cli#10108)
- Real API token survey: GitHub, Auth0, Okta, Django REST, Laravel, Supabase, Firebase, Keycloak, Express, Strapi, AWS Cognito, Microsoft Entra
