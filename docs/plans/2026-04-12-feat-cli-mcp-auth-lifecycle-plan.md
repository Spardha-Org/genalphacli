---
title: "feat: CLI & MCP auth lifecycle — automatic token management"
type: feat
status: active
date: 2026-04-12
---

# feat: CLI & MCP Auth Lifecycle — Automatic Token Management

## Overview

Generated CLI tools and MCP servers will automatically handle the auth lifecycle: detect login endpoints, generate login/authenticate commands, extract tokens from responses, store them in a shared config file, and reuse across both tools.

Auth detection is a **separate, framework-agnostic Temporal activity** that works on the route graph — not source code. Any future parser (FastAPI, Spring Boot, Express, Django) just needs to produce a route graph, and auth detection works automatically.

## Problem Statement

Generated CLIs require users to manually `export TOKEN=...` before any authenticated command works. There's no login flow, no token persistence, and no way for MCP servers to acquire tokens without manual env var setup.

## Proposed Solution

### Architecture

```
ParseWorkflow
  1. clone_repo_activity           ← framework-agnostic
  2. parse_routes_activity         ← framework-specific
  3. detect_auth_activity (NEW)    ← framework-agnostic, works on route_graph
     a. Filter: POST routes with credential-like params → candidates[]
     b. LLM: classify candidates → ranked auth endpoints with reasoning
     c. Store candidates in service metadata
  4. update status → "parsed"
                ↓
Frontend (service detail page)
  5. Show "Configure Auth" modal with LLM-ranked candidates
  6. User confirms auth endpoint(s) — login, refresh, etc.
  7. Auth config saved on service
                ↓
GenerateWorkflow (existing, enhanced)
  8. Generator reads confirmed auth config
  9. Generates login command, auth.py module, authenticate MCP tool
                ↓
Runtime
  10. mycli login → call confirmed endpoint → cascade extract token → save auth.json
  11. All commands read token from env var → auth.json → 401 hint
```

## Technical Approach

### Phase 1: Auth Detection Activity (Worker)

#### 1a. New schema: `DetectAuthInput` / `DetectAuthOutput`

**File:** `worker/activities/schemas.py`

```python
@dataclass
class DetectAuthInput:
    """Input for detect_auth_activity — framework-agnostic."""
    route_graph: dict       # CommandGraph as dict
    service_id: str

@dataclass
class AuthCandidate:
    """A route identified as a potential auth endpoint."""
    endpoint: str           # e.g., "/login/access-token"
    method: str             # "POST"
    params: list[str]       # ["username", "password"]
    response_model: str     # "Token"
    role: str               # "login" | "refresh" | "register" | "unknown"
    confidence: float       # 0.0 - 1.0
    reasoning: str          # LLM's explanation

@dataclass
class DetectAuthOutput:
    candidates: list[dict]  # list of AuthCandidate as dicts
    auth_type: str          # "bearer" | "api_key" | "none" (detected)
```

#### 1b. Filter step — narrow candidates from route graph

**File:** `worker/activities/auth_activities.py`

This is the **cheap, fast pre-filter** before the LLM call. Works on any route graph regardless of framework:

```python
def _filter_auth_candidates(route_graph: dict) -> list[dict]:
    """Filter routes that could be auth endpoints. Framework-agnostic."""
    candidates = []
    for cmd in route_graph.get("subcommands", []):
        if cmd["method"].upper() != "POST":
            continue

        param_names = {p["name"].lower() for p in cmd.get("params", [])}

        # Must have at least one credential-like param
        cred_params = param_names & {
            "password", "passwd", "pass", "secret", "pin", "otp", "code",
            "token", "refresh_token", "grant_type",
        }
        identity_params = param_names & {
            "username", "email", "login", "user", "phone", "account",
        }

        if cred_params or identity_params:
            candidates.append({
                "endpoint": cmd["endpoint"],
                "method": cmd["method"],
                "name": cmd["name"],
                "params": [p["name"] for p in cmd.get("params", [])],
                "response_model": cmd.get("output", {}).get("response_model", ""),
                "description": cmd.get("description", ""),
            })

    return candidates
```

If no candidates found, also include POST routes whose path contains auth-related segments (`/login`, `/signin`, `/auth`, `/token`, `/session`, `/oauth`) as lower-confidence fallbacks.

#### 1c. LLM classification step

**File:** `worker/activities/auth_activities.py`

Pass the filtered candidates to an LLM with a structured prompt:

```python
@activity.defn
def detect_auth_activity(input: DetectAuthInput) -> DetectAuthOutput:
    """Detect auth endpoints from route graph. Framework-agnostic."""

    candidates = _filter_auth_candidates(input.route_graph)

    if not candidates:
        return DetectAuthOutput(candidates=[], auth_type="none")

    # LLM classification
    classified = _classify_with_llm(candidates, input.route_graph)

    # Detect auth type from route graph metadata
    auth_type = input.route_graph.get("auth", {}).get("type", "none")

    return DetectAuthOutput(candidates=classified, auth_type=auth_type)
```

LLM prompt structure:

```
You are analyzing API routes to identify authentication endpoints.

Here are POST routes that may be auth-related:
{candidates as JSON}

For each route, classify its role:
- "login" — primary endpoint that accepts credentials and returns a token
- "refresh" — refreshes an expired token using a refresh token
- "register" — creates a new user account (NOT a login endpoint)
- "logout" — invalidates a session/token
- "unknown" — not an auth endpoint

Return JSON: [{"endpoint": "...", "role": "...", "confidence": 0.0-1.0, "reasoning": "..."}]
```

**LLM provider:** Use the same LLM config the platform already uses (env var / settings). Keep it pluggable — today it's Claude API, tomorrow could be anything.

#### 1d. Store results in service metadata

The `detect_auth_activity` output is stored via `update_service_status` in the service's `metadata_json`:

```json
{
  "auth_candidates": [
    {
      "endpoint": "/login/access-token",
      "method": "POST",
      "params": ["username", "password"],
      "response_model": "Token",
      "role": "login",
      "confidence": 0.95,
      "reasoning": "Accepts username/password, returns Token model, path contains 'login'"
    },
    {
      "endpoint": "/login/test-token",
      "method": "POST",
      "params": [],
      "response_model": "UserPublic",
      "role": "unknown",
      "confidence": 0.1,
      "reasoning": "No credential params, tests an existing token"
    }
  ],
  "auth_type": "bearer"
}
```

#### 1e. Integrate into ParseWorkflow

**File:** `worker/workflows/parse_workflow.py`

Add as step 3, after parse_routes_activity, before final status update:

```python
# Step 3: Detect auth endpoints (framework-agnostic)
auth_result = await workflow.execute_activity(
    detect_auth_activity,
    DetectAuthInput(
        route_graph=parse_result.route_graph,
        service_id=input.service_id,
    ),
    start_to_close_timeout=timedelta(seconds=30),
    retry_policy=RetryPolicy(maximum_attempts=2),
)

# Include auth candidates in final metadata
metadata = {
    ...existing metadata...,
    "auth_candidates": auth_result.candidates,
    "auth_type": auth_result.auth_type,
}
```

Also add to `PyPIParseWorkflow` — same activity, same position.

### Phase 2: Frontend — Auth Confirmation Modal

#### 2a. Service detail page — "Configure Auth" step

**File:** `web/src/app/(app)/services/[id]/page.tsx`

After parsing completes (status = "parsed"), before Generate tab:

- Check `service.metadata?.auth_candidates` — if non-empty, show auth config prompt
- Display modal/section with LLM-ranked candidates
- User confirms which endpoint is login, which is refresh (if any)
- "None of these" option for APIs with no login endpoint

#### 2b. Auth config modal UI

```
┌─────────────────────────────────────────────┐
│ Configure Authentication                     │
│                                              │
│ We detected these potential auth endpoints:  │
│                                              │
│ ● POST /login/access-token          95%     │
│   "Accepts username/password, returns Token" │
│   Role: [Login ▼]                           │
│                                              │
│ ○ POST /auth/refresh                 80%     │
│   "Refreshes expired token"                  │
│   Role: [Refresh ▼]                         │
│                                              │
│ ○ None — this API uses external auth         │
│                                              │
│              [Confirm]  [Skip]               │
└─────────────────────────────────────────────┘
```

#### 2c. API endpoint to save auth config

**File:** `services/core/routes/services.py` (or new `auth_config.py`)

```
POST /services/{service_id}/auth-config
{
  "login_endpoint": "/login/access-token",
  "login_params": ["username", "password"],
  "refresh_endpoint": "/auth/refresh",    // optional
  "auth_type": "bearer"
}
```

Stores in `service.metadata_json.auth_config` (confirmed by user).

#### 2d. Frontend API + hook

```typescript
// api.ts
servicesApi.setAuthConfig = (serviceId, config) =>
  apiFetch(`/services/${serviceId}/auth-config`, { method: "POST", body: ... })

// hooks.ts
useSetAuthConfig()
```

### Phase 3: Generator Changes

#### 3a. Read confirmed auth config in generator

The generator reads `service.metadata_json.auth_config` (user-confirmed) instead of heuristic guesses. If no auth config was confirmed, fall back to env-var-only mode (current behavior).

#### 3b. `_build_context()` additions

**File:** `src/genalphacli/generators/pip_generator.py`

```python
# Added to context dict:
"has_auth_lifecycle": bool(auth_config),
"auth_endpoint": auth_config.get("login_endpoint", ""),
"auth_method": "POST",
"auth_params": auth_config.get("login_params", []),
"refresh_endpoint": auth_config.get("refresh_endpoint", ""),
```

#### 3c. New template: `auth.py.j2`

**File:** `src/genalphacli/generators/templates/pip_package/auth.py.j2`

Shared token management module generated into both CLI and MCP packages:

- `get_token()` — resolve: env var → auth.json → empty
- `extract_token(response)` — cascading extraction (common keys → wrappers → JWT pattern → ask user)
- `save_auth(token, field_path)` — atomic write to `~/.config/{cli_name}/auth.json` with 0o600
- `load_auth()` / `clear_auth()` — read/delete auth.json

#### 3d. CLI template additions — `cli.py.j2`

Conditional `login`, `logout`, `auth-status` commands (only when `has_auth_lifecycle` is true):

- `login` — prompts for params (password masked), calls auth endpoint, cascading extraction, saves token
- `logout` — deletes auth.json
- `auth-status` — shows token source (env var vs auth.json), creation time

#### 3e. MCP template additions — `server.py.j2`

Conditional `authenticate` and `refresh_auth` tools:

- `authenticate(username, password)` — calls auth endpoint, extracts token, saves to shared auth.json
- `refresh_auth()` — uses refresh token or re-auths

#### 3f. Client template changes — `client.py.j2` (both pip and mcp)

Token resolution: env var → auth.json → empty. 401 error says "Run {cli_name} login".

### Phase 4: Service Status Update Endpoint

#### 4a. New endpoint for auth config

**File:** `services/core/routes/services.py`

```python
@router.post("/services/{service_id}/auth-config")
async def set_auth_config(service_id: str, body: AuthConfigRequest, db: DbDep):
    """Save user-confirmed auth config on a service."""
    service = ...  # look up
    metadata = service.metadata_json or {}
    metadata["auth_config"] = body.model_dump()
    service.metadata_json = metadata
    await db.commit()
    return {"ok": True}
```

#### 4b. Frontend proxy route

**File:** `web/src/app/api/services/[[...path]]/route.ts` — already proxies POST to Core, no changes needed.

## File Manifest

| File | Action | Description |
|------|--------|-------------|
| `worker/activities/schemas.py` | Edit | Add `DetectAuthInput`, `DetectAuthOutput` |
| `worker/activities/auth_activities.py` | Create | Filter + LLM classify auth endpoints |
| `worker/workflows/parse_workflow.py` | Edit | Add detect_auth_activity as step 3 |
| `worker/workflows/pypi_parse_workflow.py` | Edit | Same — add detect_auth_activity |
| `worker/worker.py` | Edit | Register new activity |
| `services/core/routes/services.py` | Edit | Add POST /services/{id}/auth-config |
| `web/src/app/(app)/services/[id]/page.tsx` | Edit | Auth confirmation modal after parsing |
| `web/src/data/api.ts` | Edit | Add setAuthConfig method |
| `web/src/data/hooks.ts` | Edit | Add useSetAuthConfig hook |
| `src/genalphacli/generators/pip_generator.py` | Edit | Add auth context vars, generate auth.py |
| `src/genalphacli/generators/mcp_generator.py` | Edit | Generate auth.py into MCP package |
| `src/genalphacli/generators/templates/pip_package/auth.py.j2` | Create | Shared token management module |
| `src/genalphacli/generators/templates/pip_package/cli.py.j2` | Edit | Add login/logout/auth-status commands |
| `src/genalphacli/generators/templates/pip_package/client.py.j2` | Edit | Token resolution: env var → auth.json |
| `src/genalphacli/generators/templates/mcp_package/server.py.j2` | Edit | Add authenticate/refresh_auth tools |
| `src/genalphacli/generators/templates/mcp_package/client.py.j2` | Edit | Token resolution: env var → auth.json |

## Acceptance Criteria

### Functional

- [ ] `detect_auth_activity` filters POST routes with credential-like params
- [ ] LLM classifies candidates with role + confidence + reasoning
- [ ] Auth candidates stored in service metadata after parsing
- [ ] Frontend shows auth confirmation modal with ranked candidates
- [ ] User can confirm login endpoint, refresh endpoint, or skip
- [ ] Confirmed auth config saved on service via POST /services/{id}/auth-config
- [ ] Generator reads confirmed config and produces login command + auth.py
- [ ] Generated CLI has `login`, `logout`, `auth-status` commands
- [ ] Token extracted using cascading confidence (common keys → wrappers → JWT → ask user)
- [ ] Token stored in `~/.config/{cli_name}/auth.json` with 600 permissions
- [ ] All commands resolve token: env var → auth.json → empty
- [ ] 401 response shows "Run {cli_name} login" hint
- [ ] MCP server has `authenticate` and `refresh_auth` tools sharing auth.json
- [ ] Auth detection works on any route graph (not tied to FastAPI)

### Non-Functional

- [ ] Auth detection activity completes in <30s (LLM call + filter)
- [ ] No new dependencies in generated packages (auth.py is stdlib only)
- [ ] Backward compatible — services without auth config generate like before

## Edge Cases

| Case | Behavior |
|------|----------|
| No auth candidates found | `detect_auth_activity` returns empty list. No modal shown. Env var mode. |
| LLM unavailable | Skip classification, return filtered candidates with role="unknown" |
| User clicks "Skip" on modal | No auth config saved. Generator produces env-var-only code. |
| API with only API key (no login) | No candidates. User exports env var as before. |
| Multiple login endpoints | LLM ranks them. User picks one in modal. |
| Future Java/Express parser | Just needs to produce a route graph. Auth detection works automatically. |

## Research: Prior Art

**No existing tool solves this end-to-end.** Token extraction from unknown response shapes is novel.

| Pattern | Source | How we use it |
|---------|--------|---------------|
| Login endpoint path heuristics | AuthREST paper (arxiv 2509.10320, 100 APIs) | Param filter: `password` > `pass`, `username` > `email` > `login` |
| `tokenUrl` from OpenAPI securitySchemes | Speakeasy, Fern | Highest-confidence signal — direct LLM input |
| JWT regex detection | Standard | `/^eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/` in cascade |
| Credential chain | AWS CLI | env var → config file → prompt |
| Atomic file writes | GitHub CLI | `os.replace()` cross-platform atomic |

## References

- Brainstorm: `docs/brainstorms/2026-04-12-cli-mcp-auth-lifecycle-brainstorm.md`
- Existing auth detection: `src/genalphacli/config_detector.py`
- Parse workflow: `worker/workflows/parse_workflow.py`
- CLI template: `src/genalphacli/generators/templates/pip_package/cli.py.j2`
- MCP template: `src/genalphacli/generators/templates/mcp_package/server.py.j2`
- Client template: `src/genalphacli/generators/templates/pip_package/client.py.j2`
