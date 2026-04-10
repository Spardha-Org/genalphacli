---
date: 2026-04-10
topic: backend-auth-layer
---

# Backend Auth Layer — Two-Service Architecture

## What We're Building

Two separate Python FastAPI backend services for the genalphacli web app, following the ESD ↔ TPS separation pattern from Atomicwork:

1. **Core Service (:8000)** — Platform login, user management, workspace/project/service CRUD. This is the GenAlpha equivalent of ESD. If TPS goes down, users can still log in, view their dashboard, and access existing data.

2. **TPS Service (:8001)** — App marketplace, OAuth integration management, token storage/refresh, third-party API proxying. This is the GenAlpha equivalent of TPS. Handles all third-party provider interactions.

**The separation principle:** Core never stores third-party tokens. Core only stores `integration_id` references. When Core needs to clone a repo, it calls TPS with the `integration_id` and TPS handles the authenticated API call.

## Why Two Services

The original plan had Auth.js in Next.js handling everything — platform auth AND GitHub OAuth. This broke (oauth4webapi `iss` validation) and was tightly coupled.

Learned from ESD ↔ TPS at Atomicwork:
- **ESD (core)** never crashes because Slack OAuth is broken
- **TPS** can be restarted, upgraded, or have a handler bug without affecting login
- Service boundary is clear: ESD manages WHAT, TPS manages HOW (for external systems)
- `tenant_id` header on all TPS calls provides multi-tenant isolation
- `integration_id` is the only reference Core stores — no tokens, no secrets

## Key Decisions

- **Two FastAPI services**: Core (:8000) and TPS (:8001), separate processes
- **Platform auth in Core**: Email magic link only for MVP. Email/password and social login deferred to post-MVP.
- **App integrations in TPS**: TPS-style pluggable handler architecture — GitHub only for MVP
- **Token storage**: TPS owns its own `integrations` table with encrypted tokens. Core never sees tokens.
- **Service-to-service calls**: Core → TPS via HTTP with `tenant_id` (workspace_id) header. No mutual TLS for MVP (same Docker network).
- **Frontend communication**: Next.js proxies to Core (:8000). Core proxies to TPS (:8001) when needed. Frontend never talks to TPS directly.
- **Failure isolation**: If TPS is down, Core returns 502 for integration-related ops. Login, dashboard, viewing existing parsed data all still work.
- **MVP provider**: GitHub only in TPS. Architecture supports adding GitLab, Bitbucket, Gitpod via new handler classes.
- **Session management**: Server-side sessions in PostgreSQL (httpOnly cookie with session token). No JWTs for MVP — simpler, revocable.
- **DB schema ownership**: Same PostgreSQL instance, separate schemas (`core` and `tps`). No cross-schema foreign keys — only `integration_id` text references via API.
- **Temporal worker → TPS**: Worker calls TPS directly with `workspace_id` header + `integration_id` for authenticated clone operations.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│  NEXT.JS (:3000)                                              │
│  React UI + API Routes (thin proxies)                         │
│  /api/auth/*        → Core :8000                              │
│  /api/users/*       → Core :8000                              │
│  /api/workspaces/*  → Core :8000                              │
│  /api/projects/*    → Core :8000                              │
│  /api/services/*    → Core :8000                              │
│  /api/integrations/* → Core :8000 (Core proxies to TPS)       │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP (internal)
┌──────────────────────────┼───────────────────────────────────┐
│  CORE SERVICE (:8000)    ▼                                    │
│  Platform Auth + Business Logic                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Auth: magic-link send, magic-link verify, session       │  │
│  │ Users: profile, settings                               │  │
│  │ Workspaces: CRUD, members, limits                      │  │
│  │ Projects: CRUD                                         │  │
│  │ Services: CRUD, status, parse trigger, download        │  │
│  │                                                        │  │
│  │ Integration proxy (thin):                              │  │
│  │   GET  /integrations/* → forward to TPS :8001          │  │
│  │   POST /integrations/* → forward to TPS :8001          │  │
│  │   (adds workspace_id header, validates session)        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  DB: users, sessions, workspaces, workspace_members,          │
│      projects, services (with integration_id FK, no tokens)   │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP + workspace_id header
┌──────────────────────────┼───────────────────────────────────┐
│  TPS SERVICE (:8001)     ▼                                    │
│  App Marketplace + OAuth + Third-Party Proxying               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Marketplace: list apps, app metadata                   │  │
│  │ Install: start OAuth flow, exchange code, store token  │  │
│  │ Integrations: list connected apps, disconnect          │  │
│  │ Proxy: clone repo, list repos (auto-refresh tokens)    │  │
│  │                                                        │  │
│  │ Handlers (pluggable):                                  │  │
│  │   GitHubHandler  → install, exchange, refresh, repos   │  │
│  │   GitLabHandler  → (future)                            │  │
│  │   BitbucketHandler → (future)                          │  │
│  │   GitpodHandler  → (future)                            │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  DB: app_marketplace, integrations (encrypted tokens)         │
│  (separate tables, same PostgreSQL instance for MVP)          │
└──────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────────┐
│  TEMPORAL WORKER                                              │
│  ParseWorkflow calls TPS to clone repos with integration_id   │
│  GenerateWorkflow operates on local files (no TPS needed)     │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow Examples

### User signs up + connects GitHub
```
1. User → Next.js → Core: POST /auth/register {email, password}
2. Core creates user + workspace + default project → returns session
3. User → Next.js → Core → TPS: POST /integrations/github/install
4. TPS returns GitHub OAuth URL → user redirected to GitHub
5. GitHub callback → Next.js → Core → TPS: GET /integrations/github/callback?code=xxx
6. TPS exchanges code for token, encrypts, stores in integrations table
7. TPS returns integration_id to Core
8. Core stores integration_id on the workspace record
```

### User parses a repo
```
1. User → Next.js → Core: POST /services {repo_url, project_id}
2. Core checks user has a GitHub integration → gets integration_id
3. Core starts ParseWorkflow with integration_id
4. Temporal worker → TPS: POST /integrations/{integration_id}/clone {repo_url}
5. TPS auto-refreshes token if needed, clones repo, returns path
6. Worker runs pipeline on cloned repo → stores graph in Core DB
```

### TPS is down
```
1. User → Next.js → Core: GET /dashboard → Works (Core DB only)
2. User → Next.js → Core: GET /services → Works (Core DB only)
3. User → Next.js → Core: POST /services → Fails with 502 "Integration service unavailable"
4. User → Next.js → Core: POST /integrations/github/install → Fails with 502
5. Everything else (login, view data, manage projects) → Works fine
```

## Pattern Mapping (Atomicwork → GenAlpha)

| Atomicwork (Java) | GenAlpha (Python/FastAPI) |
|---|---|
| ESD main-api (:8080) | Core Service (:8000) |
| TPS (:8093) | TPS Service (:8001) |
| `tenant_id` header | `workspace_id` header |
| `IntegrationApi` Jersey client | `httpx` async client in Core (`tps_client.py`) |
| `integration_id` in ESD entities | `integration_id` on workspace/service records |
| `ThirdPartyAppConfig.java` | `TPS_URL` env var + httpx timeout config |
| SQS FIFO for async ops | Direct HTTP for MVP |
|---|---|
| `AppMarketPlaceEntity` | `app_marketplace` table + Pydantic model |
| `IntegrationEntity` (encrypted config) | `integrations` table + Fernet encryption |
| `IAppInstallHandler<T>` | `AppHandler` Protocol class |
| `GithubHandler implements IAppInstallHandler` | `GithubHandler(AppHandler)` |
| `ClientConfigResolver.getOrRefresh()` | `IntegrationService.get_or_refresh()` |
| `{App}ProxyImpl` | `{App}Proxy` class (httpx client) |
| `NativeAppHandlerFactory` | `handler_registry: dict[AppType, AppHandler]` |
| `EncryptedHashMapConverter` | `encrypt_config()` / `decrypt_config()` with Fernet |

## Open Questions

_None — all resolved during brainstorm._

## Next Steps

→ `/workflows:plan` for implementation details
→ Remove Auth.js from Next.js entirely
→ Build Core Service (platform auth + business logic)
→ Build TPS Service (app marketplace + OAuth handlers)
→ Update Next.js to proxy to Core instead of handling auth
→ Update Temporal worker to call TPS for authenticated clone operations
→ Add both services to docker-compose.yml
