---
date: 2026-04-11
topic: tps-architecture-rewrite
---

# TPS Architecture Rewrite

## What We're Building

Rewrite the Python TPS from a single-app GitHub OAuth service into a fully extensible app integration platform, modeled after the Java TPS at Atomicwork. The architecture should support any number of apps with different auth types, but ship with only GitHub initially.

### Core changes:
1. **App marketplace as DB-driven registry** with Alembic migrations (not seed functions)
2. **5 auth types**: OAuth2, API Key, Basic Auth, Form-based OAuth2, mTLS
3. **Provider abstraction** (interface only, Native provider implemented)
4. **Token refresh with expiry tracking** — proactive refresh before API calls
5. **Per-app handler pattern** — each app gets its own handler class
6. **App categories and groups** — Source Control, Hosting, Coming Soon, etc.
7. **Encrypted token storage** — keep Fernet, add `expires_at` tracking

### NOT building (yet):
- Actions system (GITHUB_LIST_ISSUES, etc.) — GenAlpha doesn't need per-app API operations
- Call API generic proxy — not needed until workflow automation
- Redis token caching — DB-only at current scale
- Tray/IntegrationApp/Nango providers — only Native for now
- SQS webhooks — no inbound event processing needed
- MCP server registry — separate concern

## Why This Approach

### Architecture-first, apps-later
Building the full extensible architecture with only GitHub means we validate the patterns without spreading thin across multiple OAuth flows and API quirks. Adding GitLab, Bitbucket, Cloudflare later is just "add a handler + migration" — no structural changes needed.

### Alembic over create_all
The current `create_all` approach can't add columns to existing tables, can't seed app data reliably, and has no rollback story. Alembic gives us version-controlled schema + data migrations — critical for a table like `app_marketplace` that grows via INSERT migrations (one per app, just like Flyway in the Java TPS).

### Native provider only (with interface)
The `AppProvider` enum and `IntegrationService` interface exist in code, but only `NativeIntegrationService` is implemented. This means adding Tray later is "implement the interface" — zero refactoring.

### DB-only token management (no Redis)
At GenAlpha's scale (single-digit concurrent users), the `get_or_refresh` pattern hitting PostgreSQL directly is sub-millisecond. Redis adds infra complexity for a problem that doesn't exist yet.

## Key Decisions

### Schema Design (from Java TPS patterns)

**`tps_app_marketplace`** (enhanced):
- `apps` enum integer (unique) — stable ID per app, like Java's `Apps(14)` for GitHub
- `app_name` string (unique) — human key like `"github"`
- `display_name` — "GitHub"
- `auth_type` enum — `oauth2`, `api_key`, `basic_auth`, `form_based_oauth2`, `mtls`
- `category` enum — `source_control`, `hosting`, `coming_soon`
- `provider` enum — `native` (only one for now)
- `meta` JSON — icon URL, description, form field definitions (like Java's `fields` array)
- `authorize_url`, `token_url`, `scopes` — OAuth-specific, nullable for non-OAuth apps
- `is_install_required` bool — true for OAuth apps, false for API key apps
- `active` bool

**`tps_integrations`** (enhanced from current):
- Keep: `id`, `workspace_id`, `app_name`, `config_encrypted`, `status`, `created_at`, `updated_at`
- Add: `app_id` FK to marketplace (proper relationship)
- Add: `identifier` — external ID (e.g., GitHub org ID, Cloudflare account ID)
- Add: `expires_at` datetime — token expiry timestamp (null for non-expiring tokens)
- Rename: `github_username` → `display_name` (generic, works for any app)

**`tps_oauth_states`** (keep as-is, add TTL cleanup)

### Auth Type Handling

Each auth type follows a different flow:

| Auth Type | Install Flow | Token Storage | Refresh |
|-----------|-------------|---------------|---------|
| OAuth2 | Redirect → code exchange | `{access_token, refresh_token, expires_at}` | Auto-refresh via handler |
| API Key | User submits form (token field) | `{api_token}` or `{api_token, org_url}` | Never expires |
| Basic Auth | User submits form (user + pass) | `{username, password}` | Never expires |
| Form-based OAuth2 | User submits client_id/secret + redirect | `{access_token, refresh_token, client_id, client_secret}` | Refresh with tenant's own credentials |
| mTLS | User uploads cert + key | `{certificate, private_key}` | Cert expiry tracked |

### Handler Pattern

```
handlers/
  base.py          # AppHandler Protocol (existing, extended)
  registry.py      # HANDLER_REGISTRY dict
  github.py        # OAuth2 handler
  # Future: gitlab.py, bitbucket.py, cloudflare.py
```

The `AppHandler` protocol gets new optional methods:
- `get_form_fields() -> list[dict]` — returns form field definitions for API key/credential apps
- `validate_credentials(config) -> bool` — tests if stored credentials work (for API key apps)
- `revoke_token(config) -> None` — proper token revocation on disconnect

### Config Changes

Per-app env vars for platform OAuth credentials:
```
TPS_GITHUB_CLIENT_ID=...
TPS_GITHUB_CLIENT_SECRET=...
TPS_GITHUB_REDIRECT_URI=...
TPS_GITLAB_CLIENT_ID=...
TPS_GITLAB_CLIENT_SECRET=...
```
Each handler reads its own env vars. Non-OAuth apps (API Key, Basic Auth) have no platform credentials — everything comes from the user at connect time.

### Migration Strategy

1. Initialize Alembic in `services/tps/`
2. First migration: create enhanced `tps_app_marketplace` table (replacing current)
3. Second migration: alter `tps_integrations` (add columns)
4. Third migration: INSERT GitHub app into marketplace
5. Future apps: one migration each (INSERT + handler file)

## Resolved Questions

- **Scope?** Architecture-first with only GitHub. Apps added later via handler + migration.
- **Providers?** Native only. Interface exists for future Tray/iPaaS support.
- **Migrations?** Alembic — version-controlled schema + data migrations.
- **Actions system?** Skip. GenAlpha doesn't need per-app API operations yet.
- **Token caching?** No Redis. DB-only refresh is fine at current scale.
- **Initial apps?** GitHub only. GitLab, Bitbucket, Cloudflare come next.
- **Per-app OAuth credentials?** Hybrid by nature:
  - Platform OAuth creds (`client_id`/`client_secret`) → env vars (`TPS_GITHUB_CLIENT_ID`, etc.). Same for all users, deploy-time config.
  - Per-user tokens (OAuth `access_token`/`refresh_token`, API keys, passwords) → `tps_integrations.config_encrypted`. Per-user, runtime data.
  - Tenant's own OAuth app creds (Form-based OAuth2) → also `tps_integrations.config_encrypted`. Provided at connect time.

- **Database?** Separate `tps` database. Clean service boundary, matches Java TPS pattern. Requires new Docker Compose DB + Alembic config pointing to it.

- **Frontend form fields?** Yes — `meta` JSON on `tps_app_marketplace` contains a `fields` array (like Java TPS). Each field has `reference_key`, `type`, `display_name`, `required`. Frontend renders connect modals dynamically per app. Adding a new app = migration + handler, zero frontend changes.

## Next Steps

-> `/workflows:plan` for implementation details
