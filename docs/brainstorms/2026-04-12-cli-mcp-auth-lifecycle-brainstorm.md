---
date: 2026-04-12
topic: cli-mcp-auth-lifecycle
---

# CLI & MCP Auth Lifecycle — Automatic Token Management

## What We're Building

A token management system for generated CLI tools and MCP servers that handles the full auth lifecycle: login, store, reuse, refresh, and re-auth on expiry — without requiring users to manually copy tokens into env vars.

The system works across both CLI and MCP, sharing a single token store. Whichever tool initializes the token first, the other reuses it.

## The Core Problem

Generated CLIs currently require users to manually export a token env var before any authenticated command works. This is because:

1. We don't know which endpoint is the "login" endpoint — it could be `/login`, `/signin`, `/auth/token`, anything
2. We don't know which field in the login response is the token — `access_token`, `token`, `jwt`, nested paths
3. We don't know which commands need auth — but the server does (it returns 401)

## Why This Approach

**We don't try to be omniscient at parse time.** Instead:

- **Server tells us what needs auth** — 401 response = auth required. No need for us to pre-detect.
- **Cascading token extraction** — try common keys first, fall back to pattern matching, ask user as last resort. Covers 95%+ of APIs without configuration.
- **Shared config file** — CLI and MCP both read/write `~/.config/{cli_name}/auth.json`. Login once, use everywhere.

## Key Decisions

### 1. Auth Endpoint Detection: Hybrid (parse-time + runtime fallback)

**Parse time:** Use heuristics to tag the most likely login endpoint in the route graph:
- OpenAPI: parse `securitySchemes` for `tokenUrl` (authoritative signal)
- AST: score routes by shape — POST + password-like param + token-like response model
- Tag the best match as `is_auth_endpoint: true` in the route graph

**Runtime fallback:** If no auth endpoint was tagged at parse time:
- On 401, show error + hint: "Authentication required. Run `mycli <cmd>` to login, or `export {ENV_VAR}=<token>`"
- User figures out which command is login — simplest, no magic

### 2. Token Extraction: Cascading Confidence

When a login command returns a response, extract the token using cascading confidence:

**Level 1 — High confidence (auto-use, no prompt):**
Check for keys: `access_token`, `token`, `jwt`, `id_token`, `auth_token`, `session_token`
First non-empty string match → use it.

**Level 2 — Medium confidence (JWT/token pattern matching):**
Scan all string values in response for:
- JWT pattern: starts with `eyJ` (base64 JSON header)
- Long base64 strings (>40 chars, alphanumeric + `-_`)
Auto-use the first match.

**Level 3 — Low confidence (ask user):**
Display all string fields from the response and prompt:
"Which field is your auth token?"
Store the user's choice as `token_field_path` in config for future logins.

### 3. Token Storage: Config File with Permissions Warning

Store at `~/.config/{cli_name}/auth.json`:
```json
{
  "access_token": "eyJ...",
  "token_field_path": "access_token",
  "base_url": "http://localhost:8000",
  "stored_at": "2026-04-12T10:30:00Z"
}
```

- File permissions: `0o600` (owner read/write only)
- One-time warning on first store: "Token saved to ~/.config/{cli_name}/auth.json (plaintext)"
- Env var always overrides file (power users can still export)

### 4. CLI Auth Commands

Generated CLI gets these auth-related behaviors:

- **`mycli login`** (if auth endpoint detected) — prompts for credentials, calls auth endpoint, extracts + stores token
- **Any command on 401** — "Authentication required. Run `mycli login` or export {ENV_VAR}=<token>"
- **`mycli auth refresh`** — uses stored refresh_token if available, otherwise prompts for credentials again
- **`mycli auth status`** — shows whether token exists, when it was stored, expiry if known
- **`mycli auth logout`** — deletes stored token

### 5. MCP Auth

MCP server shares the same `~/.config/{cli_name}/auth.json`:

- **`authenticate` tool** — agent calls it with credentials, server runs login flow, stores token. Works exactly like CLI login but called by the agent.
- **`refresh_token` tool** — re-authenticates when token expires
- **Auto-read from config** — if CLI already logged in, MCP server picks up the token automatically
- **401 handling** — tool returns error message telling agent to call `authenticate` first

### 6. Token Resolution Order

When making any API call, resolve the token in this order:
1. Env var (explicit override, highest priority)
2. Config file (`~/.config/{cli_name}/auth.json`)
3. Empty (no token — server may return 401)

### 7. Password Field Handling

When generating the login command, password-like params get special treatment:
- Rendered with `typer.Option(prompt=True, hide_input=True)` — masks input
- Never echoed to terminal or stored in shell history

## Resolved Questions

- **Q: How do we know which endpoints need auth?** A: We don't. The server tells us via 401. No pre-detection needed.
- **Q: How do we identify the login endpoint by name?** A: We don't rely on names. Shape-based heuristics at parse time, simple error hint at runtime fallback.
- **Q: Should we use keychain?** A: No — config file with 600 permissions. Same security model as .env files. Simpler, no extra dependency.
- **Q: What about OAuth2 flows (authorization code, PKCE)?** A: Out of scope for v1. Focus on password-grant style login (POST credentials → get token). OAuth2 redirect flows are a future enhancement.
- **Q: What about concurrent access (CLI + MCP reading/writing auth.json at the same time)?** A: Accept the race condition for v1. Both tools read-then-write atomically (write to temp file, rename). Token writes are infrequent (only on login/refresh), so collisions are unlikely in practice.

## Next Steps

Run `/workflows:plan` to design the implementation across:
- Parser (auth endpoint tagging in route graph)
- Models (AuthEndpointInfo in CommandGraph)
- Generator templates (login command, token store, 401 handling)
- MCP templates (authenticate tool, shared config)
