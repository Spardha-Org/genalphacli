# Parsing Pipeline

GenAlpha CLI uses a two-layer parsing strategy. Each layer fills gaps the previous one missed.

## Layer 1: OpenAPI Spec Detection

Scans for `openapi.json`, `swagger.yaml`, and similar files in the repo root and common directories (`/docs`, `/api-docs`, `/specs`).

- Supports OpenAPI v3 and Swagger v2
- Resolves internal `$ref` references (remote URLs blocked for security)
- Extracts response schemas and content types
- Falls back gracefully if the spec is malformed

## Layer 2: AST-Based Route Extraction

Uses Python's `ast` module to extract routes from decorators and type annotations.

### Supported Frameworks

| Framework | Status |
|---|---|
| FastAPI (`@app.get()`, `@router.post()`) | Supported |
| Flask (`@app.route()`, `@blueprint.route()`) | Planned |
| Django/DRF (`path()`, `@api_view()`, `ViewSet`) | Planned |
| Spring Boot (`@GetMapping`, `@PostMapping`) | Planned |

### Complex Patterns Handled

- **Cross-file prefix resolution**: `include_router(router, prefix="/api/v1")` tracked via import analysis
- **Router-level prefixes**: `APIRouter(prefix="/users")`
- **Async handlers**: `async def` functions
- **Docstrings**: extracted as command descriptions
- **Constant propagation**: variable paths like `PREFIX = "/api/v1"` resolved
- **Pydantic model schemas**: response models extracted with field types

### Dependency Injection Filtering

These are automatically excluded from generated commands (they're framework internals, not user-facing params):

- `Depends()` and `Annotated[X, Depends()]` annotations
- `*Dep` suffix types (e.g., `SessionDep`, `TokenDep`)
- Known DI names: `session`, `db`, `current_user`, `authorization`, `request`, `response`, `credentials`, `background_tasks`, `token`
- Framework types: `Request`, `Response`, `BackgroundTasks`, `WebSocket`

### Route Merging

When both layers produce results, they are merged using route identity `(HTTP method, normalized path)`. Path params are treated as wildcards (`/users/{id}` == `/users/{user_id}`). Later layers override earlier ones.

## Auto-Detection

| Signal | Source | Priority |
|---|---|---|
| Auth type (bearer/api_key) | `.env.example` + code patterns (`HTTPBearer`, `OAuth2`) | Auto-detected |
| Base URL | `.env.example` (`BASE_URL`, `API_URL`, `PORT`) | Auto-detected |
| Framework | Dependency files + import scanning | Auto-detected |
| CLI overrides (`--base-url`, `--auth-type`) | User flags | Highest |

## Response Format Detection

| Source | Detected Format |
|---|---|
| `application/json` / default | `json` |
| `text/html` / `HTMLResponse` | `html` |
| `text/plain` / `PlainTextResponse` | `text` |
| `FileResponse` | `file` |
| `StreamingResponse` | `stream` |
| `response_model=UserOut` | Full schema with field types |

## Type Mapping

| Python Type | Mapped Type |
|---|---|
| `str`, `UUID`, `EmailStr`, `datetime` | `string` |
| `int` | `integer` |
| `bool` | `boolean` |
| `float`, `Decimal` | `float` |
| `list`, `List[X]`, `set`, `tuple` | `list` |
| `UploadFile` | `file` |
| Pydantic models, `dict` | `json` |
