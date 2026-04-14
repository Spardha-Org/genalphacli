---
date: 2026-04-14
topic: core-service-clean-architecture
---

# Core Service — Clean Architecture Redesign

## What We're Building

A full architectural refactor of the Core service from "routes-do-everything" to clean architecture with:
- **Repository layer** — all DB access behind interfaces
- **Service layer** — all business logic in testable services
- **Thin route handlers** — validation + delegation only
- **Response schemas** — Pydantic models for every endpoint
- **HTTP-based TPS client** — true microservice boundary
- **API versioning** — `/api/v1` prefix on all routes

## The Core Problems

The current Core service has 6 critical security vulnerabilities, no service layer, no repository pattern, raw dict responses, direct TPS DB access, and massive code duplication. Business logic is tangled into route handlers making it impossible to unit test, reuse, or reason about.

## Why This Approach

**Clean architecture** because:
- Routes become 5-line functions (validate → call service → return schema)
- Services are pure business logic, testable without HTTP
- Repositories abstract DB access, swappable for tests
- Response schemas auto-generate OpenAPI docs and validate outputs
- Each layer has a single responsibility

**Not over-engineering** because:
- We already have 17 route files with duplicated patterns
- 6 security vulnerabilities need structural fixes, not patches
- The codebase will grow (more parsers, more frameworks, more deploy targets)

## Key Decisions

### 1. Directory Structure

```
services/core/
├── alembic.ini
├── main.py                     # FastAPI app, middleware, lifespan
├── config.py                   # Nested settings (db, auth, tps, temporal)
├── exceptions.py               # Domain exceptions (NotFound, Unauthorized, etc.)
├── middleware.py                # Request logging, request ID, error handler
│
├── models/                     # SQLModel DB models (pure data, no logic)
│   ├── __init__.py
│   ├── user.py
│   ├── workspace.py
│   ├── project.py
│   ├── service.py
│   └── artifact.py
│
├── schemas/                    # Pydantic request/response schemas
│   ├── __init__.py
│   ├── auth.py                 # MagicLinkRequest, SessionResponse, etc.
│   ├── project.py              # CreateProjectRequest, ProjectResponse, etc.
│   ├── service.py              # ServiceResponse, ServiceListItem, etc.
│   ├── parse.py                # ParseRequest, ParseResponse
│   ├── generate.py             # GenerateRequest, GenerateResponse
│   └── integration.py          # AppResponse, IntegrationResponse
│
├── repositories/               # DB access layer (one per aggregate)
│   ├── __init__.py
│   ├── user_repo.py            # find_by_email, create, etc.
│   ├── session_repo.py         # create, validate, cleanup_expired
│   ├── workspace_repo.py       # find_by_owner, create_with_member
│   ├── project_repo.py         # list_by_workspace, create, delete_cascade
│   ├── service_repo.py         # find_by_id_with_ownership, update_status, etc.
│   └── artifact_repo.py        # upsert, find_by_id, stream_data
│
├── services/                   # Business logic (one per domain)
│   ├── __init__.py
│   ├── auth_service.py         # login, verify, logout, session management
│   ├── project_service.py      # create, update, delete (with cascades)
│   ├── parse_service.py        # validate + start parse workflow
│   ├── generate_service.py     # validate + start generate/publish workflow
│   └── integration_service.py  # proxy to TPS via HTTP
│
├── clients/                    # External service clients
│   ├── __init__.py
│   ├── tps_client.py           # HTTP client to TPS service
│   ├── temporal_client.py      # Temporal client with lifecycle management
│   └── email_client.py         # Resend email (async)
│
├── routes/                     # Thin controllers (validate → service → schema)
│   ├── __init__.py
│   ├── v1/                     # Versioned API routes
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── projects.py
│   │   ├── services.py
│   │   ├── parse.py
│   │   ├── generate.py
│   │   ├── integrations.py
│   │   ├── artifacts.py
│   │   └── internal.py         # Worker callbacks (status update, artifact upload)
│   └── health.py               # Deep health check (DB + Temporal + TPS)
│
├── deps.py                     # FastAPI dependencies (session, auth, workspace)
├── auth/
│   ├── magic_link.py           # Token generation/verification
│   └── oauth_state.py          # OAuth state encryption
│
└── migrations/
    ├── env.py
    └── versions/
```

### 2. Layer Rules

| Layer | Can depend on | Cannot depend on |
|-------|--------------|-----------------|
| Routes | Schemas, Services, Deps | Repositories, Models directly |
| Services | Repositories, Clients, Schemas, Exceptions | Routes, FastAPI |
| Repositories | Models, DB Session | Services, Routes, Clients |
| Clients | Config, httpx | Anything internal |
| Schemas | Nothing | Everything |
| Models | Nothing | Everything |

### 3. Security Fixes

| Vulnerability | Fix |
|--------------|-----|
| `/services/{id}/status` — no auth | Move to `/api/v1/internal/` with shared secret header (`X-Worker-Secret`) |
| `/artifacts` upload — no auth | Move to internal routes with worker secret |
| `/artifacts` download — no auth | Add workspace ownership check via service → project → workspace chain |
| `/publish` — missing ownership check | Service layer validates ownership before starting workflow |
| Hardcoded dev secrets | Remove defaults, require env vars, crash on startup if missing |
| No file size limit on upload | Add `Content-Length` check, reject > 100MB |

### 4. TPS Client — HTTP Instead of Direct DB

```python
# services/core/clients/tps_client.py
class TpsHttpClient:
    """HTTP client to TPS service. True microservice boundary."""

    def __init__(self, base_url: str, secret: str):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=10.0)
        self._secret = secret

    async def list_apps(self) -> list[dict]:
        resp = await self._get("/apps")
        return resp.json()

    async def get_integration(self, user_id: str, app_name: str) -> dict | None:
        resp = await self._get(f"/integrations/{app_name}",
                               headers={"X-User-ID": user_id})
        if resp.status_code == 404:
            return None
        return resp.json()

    async def _get(self, path: str, **kwargs) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers["X-TPS-Secret"] = self._secret
        resp = await self._client.get(path, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp

    async def close(self):
        await self._client.aclose()
```

### 5. Response Schemas (example)

```python
# services/core/schemas/service.py
class ServiceResponse(BaseModel):
    id: str
    project_id: str
    name: str
    repo_url: str | None
    source_type: str
    framework: str | None
    status: str
    route_graph: dict | None
    error_message: str | None
    artifact_id: str | None
    metadata: dict | None
    created_at: str

class ServiceListItem(BaseModel):
    id: str
    name: str
    repo_url: str | None
    framework: str | None
    status: str
    created_at: str
```

### 6. Service Layer Pattern (example)

```python
# services/core/services/parse_service.py
class ParseService:
    def __init__(self, service_repo, project_repo, tps_client, temporal_client):
        self._services = service_repo
        self._projects = project_repo
        self._tps = tps_client
        self._temporal = temporal_client

    async def start_parse(self, owner, repo, project_id, workspace) -> ParseResult:
        # 1. Validate project ownership
        project = await self._projects.find_by_id_in_workspace(project_id, workspace.id)
        if not project:
            raise NotFoundError("Project not found")

        # 2. Look up GitHub integration
        integration = await self._tps.get_integration(workspace.owner_id, "github")

        # 3. Create service record
        service = await self._services.create(
            project_id=project_id, name=repo, repo_url=f"https://github.com/{owner}/{repo}",
            source_type="github", status="cloning",
        )

        # 4. Start workflow
        workflow_id = await self._temporal.start_parse_workflow(...)

        # 5. Update service with workflow ID
        await self._services.update(service.id, parse_workflow_id=workflow_id)

        return ParseResult(service_id=service.id, workflow_id=workflow_id, status="cloning")
```

### 7. Route Handler Pattern (example)

```python
# services/core/routes/v1/parse.py
@router.post("/parse", response_model=ParseResponse)
async def start_parse(
    body: ParseRequest,
    workspace: CurrentWorkspaceDep,
    parse_service: ParseServiceDep,
):
    result = await parse_service.start_parse(
        owner=body.owner, repo=body.repo,
        project_id=body.project_id, workspace=workspace,
    )
    return ParseResponse.from_result(result)
```

5 lines. Validate → delegate → respond.

### 8. Config Redesign

```python
class DatabaseSettings(BaseModel):
    url: str  # No default — required

class AuthSettings(BaseModel):
    magic_link_secret: str  # No default — required
    magic_link_max_age: int = 900
    session_max_age: int = 604800
    cookie_secure: bool = True  # Secure by default

class TpsSettings(BaseModel):
    url: str = "http://localhost:8001"
    secret: str  # No default — required

class Settings(BaseSettings):
    environment: str = "local"  # local | staging | production
    database: DatabaseSettings
    auth: AuthSettings
    tps: TpsSettings
    temporal_address: str = "localhost:7233"
```

### 9. Internal Routes (Worker Callbacks)

Worker-to-Core callbacks (status updates, artifact uploads) move to a dedicated internal router with a shared secret:

```python
# services/core/routes/v1/internal.py
router = APIRouter(prefix="/internal", tags=["internal"])

@router.post("/services/{service_id}/status")
async def update_service_status(
    service_id: str, body: StatusUpdateRequest,
    _auth: WorkerSecretDep,  # Validates X-Worker-Secret header
):
    ...
```

### 10. Middleware Stack

```python
# main.py lifespan + middleware
app.add_middleware(CORSMiddleware, ...)
app.add_middleware(RequestIdMiddleware)      # X-Request-Id on every response
app.add_middleware(RequestLoggingMiddleware) # Log method, path, status, duration
app.add_exception_handler(DomainError, domain_error_handler)
app.add_exception_handler(Exception, generic_error_handler)
```

### 11. Model Layer Fixes (done alongside refactor)

These aren't schema changes — they're code quality fixes inside the models:
- Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` (deprecated in Python 3.12+)
- Rename `generate_cuid()` to `generate_id()` (it's not a CUID, it's `secrets.token_hex`)
- Add `onupdate` for `updated_at` fields (currently never updates)
- Use string enums for `Service.status`, `Service.source_type`, `Artifact.artifact_type`
- Add `UniqueConstraint("workspace_id", "user_id")` on `WorkspaceMember`
- Add `ondelete="CASCADE"` on FK relationships (replace manual cascade in app code)

### 12. Config Nesting Gotcha

Pydantic `BaseSettings` with nested models needs `env_nested_delimiter` to parse env vars like `CORE_DATABASE__URL` (double underscore). Set `model_config = SettingsConfigDict(env_prefix="CORE_", env_nested_delimiter="__")`. Without this, nested settings won't read from env vars.

### 13. What NOT to Change

- **TPS service** — no changes (Core switches from direct DB to HTTP)
- **Frontend** — update proxy base path from `/api/*` to `/api/v1/*` (one-line change per proxy route)

### 14. What DOES Change in Worker

Worker's `CORE_URL` and status update calls need to target the new internal routes:
- `POST {CORE_URL}/services/{id}/status` → `POST {CORE_URL}/api/v1/internal/services/{id}/status`
- `POST {CORE_URL}/services/{id}/artifacts` → `POST {CORE_URL}/api/v1/internal/services/{id}/artifacts`
- Worker must send `X-Worker-Secret` header on all internal calls

## Design Patterns

### 1. Repository Pattern
**Where:** `repositories/` — one per aggregate root (User, Project, Service, Artifact)
**Why:** Decouples business logic from SQLModel queries. Testable with in-memory fakes. Single place to add caching, pagination, or change ORM.

```python
class ServiceRepository:
    async def find_by_id_with_ownership(self, id: str, workspace_id: str) -> Service | None
    async def create(self, **kwargs) -> Service
    async def update(self, id: str, **fields) -> Service
    async def list_by_project(self, project_id: str, limit: int, offset: int) -> list[Service]
```

### 2. Service Layer (Application Service)
**Where:** `services/` — one per domain (auth, parse, generate, project)
**Why:** Business logic lives here, not in routes. Orchestrates repos + clients. Single transaction boundary. Testable without HTTP.

### 3. Dependency Injection via FastAPI Depends
**Where:** `deps.py` — wire repos and services as FastAPI dependencies
**Why:** FastAPI's `Depends()` is already a DI container. No need for a framework. Services get repos injected, routes get services injected.

```python
def get_service_repo(db: DbDep) -> ServiceRepository:
    return ServiceRepository(db)

def get_parse_service(
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repo)],
    tps: Annotated[TpsHttpClient, Depends(get_tps_client)],
    temporal: Annotated[TemporalClient, Depends(get_temporal_client)],
) -> ParseService:
    return ParseService(service_repo, project_repo, tps, temporal)

ParseServiceDep = Annotated[ParseService, Depends(get_parse_service)]
```

### 4. Unit of Work (Transaction Boundary)
**Where:** Service layer methods
**Why:** Each service method = one transaction. No more scattered `db.commit()` calls across route handlers. Repo methods don't commit — the service commits once at the end.
**Key detail:** Repos and the service share the **same AsyncSession** (injected via FastAPI `Depends`). The service holds the session, passes it to repos, and commits once at the end. No repo ever calls `commit()`.

```python
class AuthService:
    async def verify_and_login(self, token: str) -> LoginResult:
        email = verify_magic_token(token)
        user = await self._users.find_or_create(email)
        workspace = await self._workspaces.ensure_default(user)
        session = await self._sessions.create(user.id)
        await self._db.commit()  # Single commit for entire operation
        return LoginResult(user=user, session=session, workspace=workspace)
```

### 5. DTO / Schema Pattern (Data Transfer Objects)
**Where:** `schemas/` — Pydantic models for request/response
**Why:** API contract. Auto-generates OpenAPI docs. Validates inputs AND outputs. Decouples API shape from DB shape.

- `*Request` — input validation (field limits, enums, format checks)
- `*Response` — output serialization (exactly what the client sees)
- Internal models stay in `models/` — never exposed directly

### 6. Strategy Pattern (Handler Dispatch)
**Where:** Workflow dispatch in `parse_service.py`
**Why:** Multiple source types (GitHub, PyPI, future) share the same parse flow but differ in the first step. Instead of `if source_type == "github": ... elif source_type == "pypi": ...`, use a strategy.

```python
PARSE_STRATEGIES = {
    "github": ParseWorkflowConfig(workflow_name="ParseWorkflow", task_queue="genalpha-parse"),
    "pypi": ParseWorkflowConfig(workflow_name="PyPIParseWorkflow", task_queue="genalpha-parse"),
}
```

### 7. Factory Pattern (Client Lifecycle)
**Where:** `clients/` — managed in app lifespan
**Why:** Create clients on startup, dispose on shutdown. No lazy singletons with race conditions. No global mutable state.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all clients
    app.state.tps = TpsHttpClient(settings.tps.url, settings.tps.secret)
    app.state.temporal = await TemporalClient.connect(settings.temporal_address)
    app.state.email = EmailClient(settings.resend_api_key)

    yield

    # Cleanup all clients
    await app.state.tps.close()
    await app.state.temporal.close()
```

### 8. Guard Pattern (Authorization)
**Where:** `deps.py` — FastAPI dependencies that raise on unauthorized
**Why:** Auth checks happen in the dependency chain before the route handler runs. The handler never sees an unauthorized request.

```python
# Public route: no dep
# Authenticated: CurrentUserDep
# Workspace-scoped: CurrentWorkspaceDep (includes user + workspace)
# Internal (worker): WorkerSecretDep (validates X-Worker-Secret header)
```

### 9. Domain Exception Pattern
**Where:** `exceptions.py` — custom exceptions mapped to HTTP status codes
**Why:** Services throw domain exceptions (`NotFoundError`, `ForbiddenError`, `ConflictError`). Global exception handler maps them to HTTP responses. No `HTTPException` in the service layer.

```python
class DomainError(Exception):
    status_code: int = 500

class NotFoundError(DomainError):
    status_code = 404

class ForbiddenError(DomainError):
    status_code = 403

class ConflictError(DomainError):
    status_code = 409

# Global handler in main.py
@app.exception_handler(DomainError)
async def domain_error_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})
```

### 10. Pagination Pattern
**Where:** Repository layer + Response schemas
**Why:** No list endpoint should return all records. Consistent pagination across all list endpoints.

```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int

# Repository
async def list_by_workspace(self, workspace_id, limit=20, offset=0):
    count = await self._count(workspace_id)
    items = await self._query(workspace_id, limit, offset)
    return items, count

# Route
@router.get("/projects", response_model=PaginatedResponse[ProjectResponse])
```

### 11. Debounce Pattern (Session Extension)
**Where:** `repositories/session_repo.py`
**Why:** Currently every authenticated request commits a session update (`last_active_at`). 100 rapid API calls = 100 writes. Debounce: only extend if `last_active_at` was more than 5 minutes ago.

```python
class SessionRepository:
    async def validate_and_maybe_extend(self, session_id: str) -> Session:
        session = await self._find(session_id)
        if not session or session.expires_at < utc_now():
            raise UnauthorizedError("Session expired")
        # Only extend if stale (>5 min since last activity)
        if (utc_now() - session.last_active_at).total_seconds() > 300:
            session.last_active_at = utc_now()
            # Commit happens in the service layer, not here
        return session
```

### 12. Streaming Response Pattern (Artifact Download)
**Where:** `routes/v1/artifacts.py`
**Why:** Current code loads entire binary blob into memory via `artifact.file_data`. For a 50MB ZIP, that's 50MB in Python memory per download. Use `StreamingResponse` to stream chunks from DB.

```python
@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(artifact_id: str, ...):
    artifact = await artifact_service.get_with_ownership(artifact_id, workspace)
    return StreamingResponse(
        artifact_service.stream_data(artifact_id),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
    )
```

### 13. URL Builder Pattern (OAuth Flows)
**Where:** `services/integration_service.py`
**Why:** Current code manipulates OAuth URLs by splitting on `"state="` — brittle string manipulation. Use `urllib.parse` for correct URL construction.

```python
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

def _replace_state_param(authorize_url: str, new_state: str) -> str:
    parsed = urlparse(authorize_url)
    params = parse_qs(parsed.query)
    params["state"] = [new_state]
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))
```

### 14. Email Template Pattern
**Where:** `clients/email_client.py` + `templates/email/`
**Why:** Current code has inline HTML in the route handler. Move to Jinja2 templates for maintainability.

```
services/core/templates/email/
└── magic_link.html.j2
```

```python
class EmailClient:
    def __init__(self, api_key: str):
        self._env = Environment(loader=PackageLoader("services.core", "templates/email"))

    async def send_magic_link(self, email: str, link: str):
        html = self._env.get_template("magic_link.html.j2").render(link=link)
        await asyncio.to_thread(self._send, email, "Your login link", html)
```

### 15. Idempotency Key Pattern (Workflow Start)
**Where:** `services/parse_service.py`, `services/generate_service.py`
**Why:** Current workflow IDs are `f"parse-{service.id}"`. If a service is re-parsed, the ID collides with the previous (possibly still running) workflow. Append a short timestamp suffix.

```python
import time

def _workflow_id(prefix: str, service_id: str) -> str:
    ts = int(time.time())
    return f"{prefix}-{service_id}-{ts}"
    # e.g., "parse-abc123-1744600000"
```

## Flow-to-Pattern Mapping

Every user-facing flow mapped to the patterns it uses:

| Flow | Patterns Applied |
|------|-----------------|
| **Magic Link Request** | Service Layer + Email Template + Async I/O |
| **Verify + Login** | Service Layer + Unit of Work + Repository (User, Workspace, Session) |
| **Get Session** | Guard + Repository (joined query) + Debounce |
| **Logout** | Guard (cookie) + Service Layer + Repository |
| **OAuth Install** | Service Layer + URL Builder + TPS HTTP Client |
| **OAuth Callback** | Guard (validate callback_path) + Service Layer + TPS HTTP Client |
| **Projects CRUD** | Repository (cascade) + Pagination + DTO/Schema |
| **Services CRUD** | Repository + Pagination + DTO/Schema |
| **Auth Config** | Repository (JSON column) + Service Layer |
| **Parse GitHub** | Strategy + Service Layer + TPS HTTP Client + Idempotency Key |
| **Parse PyPI** | Strategy (same service, different config) + Idempotency Key |
| **Generate** | Service Layer + Guard (ownership) + Idempotency Key |
| **Publish** | Service Layer + Guard (ownership + PyPI integration) + Idempotency Key |
| **Artifact Upload** | Guard (WorkerSecretDep) + Validation (file size) |
| **Artifact Download** | Guard (ownership) + Streaming Response |
| **Integration Proxy** | Service Layer + DTO/Schema + TPS HTTP Client |
| **Status Update** | Guard (WorkerSecretDep) + Repository |
| **Health Check** | Deep Health (DB + Temporal + TPS probes) |

### Patterns NOT Used (YAGNI)

| Pattern | Why Not |
|---------|---------|
| CQRS | Single DB, read/write ratio doesn't justify separation |
| Event Sourcing | Temporal already provides event history for workflows |
| Hexagonal Architecture | Clean Architecture is sufficient, ports/adapters adds complexity |
| Abstract Repository Interface | Python's duck typing + testing with fakes is enough |
| Domain Events | No event bus yet. When needed, Temporal signals can serve this role |
| API Gateway | Frontend proxy is sufficient. Add gateway when we have mobile clients |

## Resolved Questions

- **Q: Repository pattern or just service layer?** A: Both. Repos abstract DB, services hold logic. Routes are thin.
- **Q: TPS access method?** A: HTTP client. True microservice boundary.
- **Q: API versioning?** A: Yes, `/api/v1` prefix now.
- **Q: Artifact storage?** A: Keep PostgreSQL, fix memory by streaming responses.
- **Q: How to auth worker callbacks?** A: Shared secret header (`X-Worker-Secret`) on internal routes.

## Open Questions

None — all decisions made.

## Next Steps

Run `/workflows:plan` to break this into implementation phases.
