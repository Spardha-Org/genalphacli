---
title: "feat: Add PyPI as source distribution app"
type: feat
status: completed
date: 2026-04-11
---

# feat: Add PyPI as Source Distribution App

## Overview

Add PyPI (Python Package Index) as a new app integration in TPS, enabling users to parse Python packages from PyPI source distributions the same way they currently parse GitHub repos. Users provide a PyPI package name, the system fetches the sdist tarball, extracts it, and runs the existing detect-framework + parse-routes pipeline on the source code.

## Problem Statement / Motivation

Currently, genalphacli only supports GitHub repos as a source. Users who want to generate CLI/MCP code for published Python packages must:
1. Find the source repo URL on PyPI
2. Hope the repo is public on GitHub
3. Paste the GitHub URL

This breaks for packages that don't link to GitHub, have a different source host, or where the published source differs from the repo HEAD. PyPI source distributions are the canonical, version-pinned source for every published Python package.

## Proposed Solution

### Architecture Decision: Auth Model

PyPI uses **API tokens** for uploads (the `pypi-...` macaroon format). Users authenticate via HTTP Basic Auth with username `__token__` and the token as password. Reading/downloading is public, but **uploading requires a token**. We register PyPI in TPS as a credential app (`CredentialHandler`, `auth_type=API_KEY`) with `is_install_required=False` and a **required** API token field. This:

- Uses the existing `API_KEY` auth type (no new enum needed)
- Stores the user's PyPI API token encrypted in TPS for upload operations
- The `validate_credentials` method checks token format (`pypi-` prefix + valid structure) — no server-side validation endpoint exists
- Users connect by providing their PyPI API token via the credential form

### High-Level Flow

```
User selects "PyPI" tab in parse form
        │
        v
Enters package name (e.g., "fastapi")
        │
        v
POST /parse/pypi  →  Core validates, creates Service(source_type="pypi")
        │
        v
Starts PyPIParseWorkflow on Temporal
        │
        v
fetch_pypi_sdist_activity:
   GET https://pypi.org/pypi/{package}/json
   → Find latest stable sdist URL
   → Download .tar.gz
   → Verify SHA256 digest
   → Safe extract with size limits
        │
        v
detect_framework (reuse existing)
        │
        v
parse_routes_activity (reuse existing)
        │
        v
Service status → "parsed" with route_graph
```

## Technical Approach

### Phase 1: TPS — PyPI App Registration

#### 1a. Create PyPI handler

**File:** `services/tps/handlers/pypi.py`

```python
class PyPIHandler:
    """Handler for PyPI — API token auth for uploads."""

    def get_app_name(self) -> str:
        return "pypi"

    async def get_user_info(self, config: dict) -> dict:
        # PyPI has no /whoami endpoint — cannot fetch user info from token
        return {}

    async def validate_credentials(self, config: dict) -> bool:
        """Validate PyPI API token by probing the upload endpoint.

        POST to upload.pypi.org/legacy/ with auth but no file:
        - 400 = token is valid (auth passed, body validation failed as expected)
        - 403 = token is invalid or revoked
        """
        token = config.get("api_token", "")
        if not token or not token.startswith("pypi-"):
            return False

        import httpx
        resp = httpx.post(
            "https://upload.pypi.org/legacy/",
            auth=("__token__", token),
            data={":action": "file_upload"},
            timeout=15.0,
        )
        return resp.status_code == 400  # 400 = auth passed, no file
```

Satisfies `CredentialHandler` protocol structurally.

#### 1b. Register handler

**File:** `services/tps/handlers/__init__.py`

```python
from services.tps.handlers.pypi import PyPIHandler

HANDLER_REGISTRY: dict[str, type] = {
    "github": GithubHandler,
    "pypi": PyPIHandler,
}
```

#### 1c. Seed migration

**File:** `services/tps/migrations/versions/V20_{epoch}__add_pypi_app_entity.py`

```python
# INSERT INTO tps_app_marketplace:
{
    "app_code": 20,
    "app_name": "pypi",
    "display_name": "PyPI",
    "auth_type": 2,          # API_KEY
    "category": 3,           # DISTRIBUTION
    "is_install_required": False,
    "meta": {
        "icon": "https://cdn.simpleicons.org/pypi/white",
        "description": "Python Package Index — publish and distribute Python packages",
        "keywords": ["python", "packages", "pypi", "sdist", "upload"],
        "form_fields": [
            {
                "reference_key": "api_token",
                "type": "password",
                "display_name": "PyPI API Token",
                "required": True,
                "placeholder": "pypi-..."
            }
        ]
    }
}
```

### Phase 2: PyPI Fetcher Module

#### 2a. Core PyPI client

**File:** `src/genalphacli/pypi.py`

Functions:
- `fetch_package_info(package_name: str) -> PackageInfo` — calls `https://pypi.org/pypi/{name}/json`, returns structured metadata
- `find_sdist_url(package_info: PackageInfo, version: str | None = None) -> SdistInfo` — finds the sdist for the latest stable (non-prerelease, non-yanked) version, or a specific version
- `download_sdist(url: str, dest_dir: Path, expected_sha256: str) -> Path` — downloads tarball, verifies SHA256
- `extract_sdist_safe(tar_path: Path, extract_dir: Path, max_size_bytes: int = 500_000_000) -> Path` — safe extraction with path traversal protection and size limit

**Security for tarball extraction:**

```python
import tarfile

def extract_sdist_safe(tar_path: Path, extract_dir: Path, max_size_bytes: int) -> Path:
    with tarfile.open(tar_path, "r:gz") as tar:
        # Python 3.12+ safe filter
        tar.extractall(path=extract_dir, filter="data")

    # Verify extracted size
    total = sum(f.stat().st_size for f in extract_dir.rglob("*") if f.is_file())
    if total > max_size_bytes:
        shutil.rmtree(extract_dir)
        raise ValueError(f"Extracted size {total} exceeds limit {max_size_bytes}")

    # Return the inner directory (sdists have a single top-level dir)
    subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
    return subdirs[0] if len(subdirs) == 1 else extract_dir
```

**Data classes:**

```python
@dataclass
class PackageInfo:
    name: str
    version: str           # latest stable version
    summary: str
    author: str | None
    license: str | None
    home_page: str | None
    releases: dict          # version -> list of file dicts

@dataclass
class SdistInfo:
    filename: str
    url: str
    sha256: str
    size: int
    version: str
```

#### 2b. HTTP best practices

- Set `User-Agent: genalphacli/1.0` header on all PyPI requests
- Respect `ETag` / `If-None-Match` for conditional requests
- Use `httpx` with 30s timeout (consistent with existing code)

### Phase 3: Worker — PyPI Activities & Workflow

#### 3a. Activity schemas

**File:** `worker/activities/schemas.py` (append)

```python
@dataclass
class FetchPyPISdistInput:
    package_name: str
    version: str | None     # None = latest stable
    service_id: str
    user_id: str

@dataclass
class FetchPyPISdistOutput:
    extract_dir: str
    framework: str | None
    package_version: str
    package_summary: str
```

#### 3b. PyPI activities

**File:** `worker/activities/pypi_activities.py`

```python
@activity.defn
def fetch_pypi_sdist_activity(input: FetchPyPISdistInput) -> FetchPyPISdistOutput:
    """Fetch a PyPI sdist, download, extract, detect framework."""
    info = fetch_package_info(input.package_name)
    sdist = find_sdist_url(info, version=input.version)

    if not sdist:
        raise ApplicationError(
            f"No source distribution found for {input.package_name}"
        )

    download_dir = Path(tempfile.mkdtemp(prefix="pypi-"))
    tar_path = download_sdist(sdist.url, download_dir, sdist.sha256)
    extract_dir = extract_sdist_safe(tar_path, download_dir / "src")
    framework = detect_framework(extract_dir)

    return FetchPyPISdistOutput(
        extract_dir=str(extract_dir),
        framework=framework,
        package_version=sdist.version,
        package_summary=info.summary,
    )
```

Reuse existing `cleanup_clone_activity` for cleanup (it just does `shutil.rmtree`).

#### 3c. PyPI Parse Workflow

**File:** `worker/workflows/pypi_parse_workflow.py`

```python
@dataclass
class PyPIParseWorkflowInput:
    package_name: str
    version: str | None
    user_id: str
    service_id: str
    command_name: str
    workspace_id: str = ""

@workflow.defn
class PyPIParseWorkflow:
    @workflow.run
    async def run(self, input: PyPIParseWorkflowInput) -> ParseWorkflowOutput:
        extract_dir = None
        try:
            # Step 1: Fetch sdist
            await workflow.execute_activity(
                update_service_status,
                StatusUpdateInput(service_id=input.service_id, status="downloading"),
                ...
            )

            fetch_result = await workflow.execute_activity(
                fetch_pypi_sdist_activity,
                FetchPyPISdistInput(...),
                start_to_close_timeout=timedelta(seconds=120),
                ...
            )
            extract_dir = fetch_result.extract_dir

            # Step 2: Parse routes (reuse existing activity)
            await workflow.execute_activity(
                update_service_status,
                StatusUpdateInput(status="parsing", framework=fetch_result.framework),
                ...
            )

            parse_result = await workflow.execute_activity(
                parse_routes_activity,
                ParseRoutesInput(
                    clone_dir=extract_dir,
                    framework=fetch_result.framework,
                    command_name=input.command_name,
                ),
                ...
            )

            # Step 3: Update status
            await workflow.execute_activity(
                update_service_status,
                StatusUpdateInput(
                    status="parsed",
                    route_graph=parse_result.route_graph,
                    metadata={
                        "source_type": "pypi",
                        "package_version": fetch_result.package_version,
                        ...
                    },
                ),
                ...
            )

            # Cleanup
            if extract_dir:
                await workflow.execute_activity(cleanup_clone_activity, extract_dir, ...)

            return ParseWorkflowOutput(...)
        except Exception:
            # Same error handling pattern as ParseWorkflow
            ...
```

#### 3d. Register workflow in worker

**File:** `worker/main.py` — add `PyPIParseWorkflow` to workflow list and `fetch_pypi_sdist_activity` to activities list.

### Phase 4: Core — Parse Endpoint & Model Changes

#### 4a. Add `source_type` to Service model

**File:** `services/core/models.py`

```python
class Service(SQLModel, table=True):
    ...
    source_type: str = Field(default="github")      # "github" | "pypi"
    source_version: Optional[str] = None             # PyPI version parsed
```

**Migration:** `V0_{epoch}__alter_services_add_source_type.py`

#### 4b. New parse endpoint

**File:** `services/core/routes/parse_pypi.py`

```python
PYPI_PACKAGE_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$")

class PyPIParseRequest(BaseModel):
    packageName: str
    projectId: str
    version: str | None = None  # None = latest stable

@router.post("/parse/pypi")
async def start_pypi_parse(body: PyPIParseRequest, workspace: CurrentWorkspaceDep, db: DbDep):
    # Validate package name
    if not PYPI_PACKAGE_RE.match(body.packageName.strip()):
        raise HTTPException(400, "Invalid PyPI package name")

    # Validate project belongs to workspace
    ...

    # Create service record
    service = Service(
        project_id=body.projectId,
        name=body.packageName.strip(),
        repo_url=f"https://pypi.org/project/{body.packageName.strip()}/",
        source_type="pypi",
        status="downloading",
    )
    ...

    # Start Temporal PyPIParseWorkflow
    await client.start_workflow(
        "PyPIParseWorkflow",
        {
            "package_name": body.packageName.strip(),
            "version": body.version,
            "user_id": workspace.owner_id,
            "service_id": service.id,
            "command_name": body.packageName.strip(),
            "workspace_id": workspace.id,
        },
        id=f"pypi-parse-{service.id}",
        task_queue="genalpha-parse",
    )
    ...
```

#### 4c. Register route

**File:** `services/core/main.py` — include `parse_pypi.router`

### Phase 5: Frontend

#### 5a. API layer

**File:** `web/src/data/api.ts`

```typescript
// Add to servicesApi:
createFromPyPI: (payload: { package_name: string; project_id: string; version?: string }) =>
  apiFetch<{ serviceId: string; workflowId: string; status: string }>(
    "/parse/pypi",
    { method: "POST", body: JSON.stringify({
      packageName: payload.package_name,
      projectId: payload.project_id,
      version: payload.version,
    }) },
  ),
```

#### 5b. Hook

**File:** `web/src/data/hooks.ts`

```typescript
export function useCreatePyPIService() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: servicesApi.createFromPyPI,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.projects() });
    },
  });
}
```

#### 5c. Parse form — source type tabs

**File:** `web/src/components/parse-form.tsx`

Add a tab switcher at the top of the form:

```
┌──────────┬──────────┐
│  GitHub  │   PyPI   │
└──────────┴──────────┘
```

- **GitHub tab** (default): existing URL input, unchanged
- **PyPI tab**: text input with placeholder `e.g., fastapi`, calls `useCreatePyPIService`

#### 5d. Service detail — source badge

**File:** service detail page/component

Show source type badge: "Parsed from PyPI: requests v2.31.0" vs "Parsed from GitHub: owner/repo"

#### 5e. Status polling

Add `"downloading"` to the `TERMINAL_STATUSES` exclusion (it's an in-progress status, not terminal). The existing polling already handles unknown non-terminal statuses correctly (refetches every 3s).

### Phase 6: Connection Form — "No Auth" State

**File:** `web/src/components/app-store/connection-form.tsx`

For apps with `auth_type === 6` (NONE), show a simplified state:

- **Not connected:** "Enable" button (calls `/connect` with empty credentials)
- **Connected:** "Enabled" badge + "Disable" button

No form fields rendered. One-click enable.

## File Manifest

| File | Action | Description |
|------|--------|-------------|
| `services/tps/models.py` | Edit | Add `AuthType.NONE = 6` |
| `services/tps/handlers/pypi.py` | Create | PyPI CredentialHandler |
| `services/tps/handlers/__init__.py` | Edit | Register PyPIHandler |
| `services/tps/migrations/versions/V20_*__add_pypi_app_entity.py` | Create | Seed migration |
| `src/genalphacli/pypi.py` | Create | PyPI client (fetch, download, extract) |
| `worker/activities/schemas.py` | Edit | Add FetchPyPISdistInput/Output |
| `worker/activities/pypi_activities.py` | Create | fetch_pypi_sdist_activity |
| `worker/workflows/pypi_parse_workflow.py` | Create | PyPIParseWorkflow |
| `worker/main.py` | Edit | Register new workflow + activity |
| `services/core/models.py` | Edit | Add source_type, source_version to Service |
| `services/core/migrations/versions/V0_*__alter_services_add_source_type.py` | Create | Schema migration |
| `services/core/routes/parse_pypi.py` | Create | POST /parse/pypi endpoint |
| `services/core/main.py` | Edit | Include parse_pypi router |
| `web/src/data/api.ts` | Edit | Add createFromPyPI |
| `web/src/data/hooks.ts` | Edit | Add useCreatePyPIService |
| `web/src/components/parse-form.tsx` | Edit | Source type tabs (GitHub/PyPI) |
| `web/src/components/app-store/connection-form.tsx` | Edit | Handle AuthType.NONE |
| `web/src/data/types.ts` | Edit | Add source_type to Service type |

## Acceptance Criteria

### Functional

- [ ] PyPI appears in App Store under "Distribution" category
- [ ] User can "enable" PyPI with one click (no credentials required)
- [ ] Parse form has GitHub/PyPI tab switcher
- [ ] User can enter a package name → system fetches sdist → parses routes → shows route graph
- [ ] Service detail shows "Parsed from PyPI: {name} v{version}"
- [ ] Temporal workflow handles: package not found, no sdist available, download failure
- [ ] Extracted tarball is secure (no path traversal, 500MB size limit)

### Non-Functional

- [ ] SHA256 digest verified on every sdist download
- [ ] `User-Agent: genalphacli/1.0` on all PyPI API requests
- [ ] Tarball extraction uses Python 3.12+ `data` filter
- [ ] Temporal retry policy: 3 attempts with exponential backoff for transient HTTP errors

## Edge Cases

| Case | Behavior |
|------|----------|
| Package not found on PyPI | Clear error: "Package '{name}' not found on PyPI" |
| No sdist available (wheels only) | Error: "No source distribution available for {name} v{version}" |
| Pre-release / yanked versions | Skip by default, use latest stable release |
| Package name with hyphens/underscores | PyPI normalizes automatically, pass through as-is |
| Oversized sdist (>500MB extracted) | Reject after extraction with size error |
| Malicious tarball (path traversal) | Blocked by `tarfile` `data` filter |

## Dependencies & Risks

- **Python 3.12+ required** for `tarfile` `data` filter. Verify worker runtime version.
- **No PyPI search API** — v1 requires exact package name input. Autocomplete is a future enhancement.
- **PyPI rate limiting** — no formal limits but respect HTTP 429. Low risk for single-user requests.

## References

- PyPI JSON API: https://docs.pypi.org/api/json/
- PEP 503 Simple API: https://peps.python.org/pep-0503/
- Source distribution format: https://packaging.python.org/en/latest/specifications/source-distribution-format/
- Tarfile security: https://docs.python.org/3/library/tarfile.html#tarfile-extraction-filter
- Existing GitHub handler: `services/tps/handlers/github.py`
- TPS migration convention: `services/tps/migrations/MIGRATIONS.md` (app_code 20 pre-assigned for PyPI)
- Related PR: NandishNaik01/genalphacli#17 (private repo auth fix)
