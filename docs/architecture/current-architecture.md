# GenAlpha CLI — System Architecture

## System Context Diagram

```mermaid
graph TB
    User([User / Developer])
    Agent([AI Agent / Claude])

    User -->|Browser| Frontend
    User -->|Terminal| GeneratedCLI
    Agent -->|MCP Protocol| GeneratedMCP

    subgraph GenAlpha Platform
        Frontend[Next.js Frontend<br/>:3000]
        Core[Core Service<br/>FastAPI :8000]
        TPS[TPS Service<br/>FastAPI :8001]
        Worker[Temporal Worker]
        Temporal[Temporal Server<br/>:7233]
        CoreDB[(Core DB<br/>PostgreSQL)]
        TPSDB[(TPS DB<br/>PostgreSQL)]
    end

    Frontend -->|/api/* proxy| Core
    Core -->|HTTP| TPS
    Core -->|Start Workflow| Temporal
    Worker -->|Poll Tasks| Temporal
    Worker -->|Update Status| Core
    Worker -->|Fetch Tokens| TPS
    Core -->|CRUD| CoreDB
    TPS -->|CRUD| TPSDB

    subgraph External
        GitHub[GitHub API]
        PyPI[PyPI Registry]
        npm[npm Registry]
        Resend[Resend Email]
    end

    Worker -->|Clone Repos| GitHub
    Worker -->|Upload Packages| PyPI
    TPS -->|OAuth Flow| GitHub
    TPS -->|Validate Tokens| PyPI
    TPS -->|Validate Tokens| npm
    Core -->|Send Magic Link| Resend

    subgraph Generated Output
        GeneratedCLI[Generated CLI<br/>pip package]
        GeneratedMCP[Generated MCP<br/>pip package]
    end

    Worker -->|Generate| GeneratedCLI
    Worker -->|Generate| GeneratedMCP
```

## Service Architecture (Component Diagram)

```mermaid
graph LR
    subgraph "Core Service :8000"
        direction TB
        AuthRoutes[Auth Routes<br/>/auth/*]
        ProjectRoutes[Project Routes<br/>/projects/*]
        ServiceRoutes[Service Routes<br/>/services/*]
        ParseRoute[Parse Route<br/>/parse, /parse/pypi]
        GenerateRoute[Generate Route<br/>/generate]
        PublishRoute[Publish Route<br/>/publish]
        ArtifactRoutes[Artifact Routes<br/>/artifacts/*]
        IntegrationProxy[Integration Routes<br/>/integrations/*]
        OAuthCallback[OAuth Callback<br/>/oauth/callback]

        CoreModels[Models<br/>User, Session, Workspace<br/>Project, Service, Artifact]
        TpsClient[TPS Client SDK]
        TemporalClient[Temporal Client]
    end

    subgraph "TPS Service :8001"
        direction TB
        AppRoutes[App Routes<br/>/apps/*]
        IntegRoutes[Integration Routes<br/>/integrations/*]

        Handlers[Handler Registry<br/>GitHub, PyPI, npm]
        IntegService[Integration Service<br/>create, refresh, delete]
        Crypto[Crypto<br/>MultiFernet encrypt/decrypt]

        TPSModels[Models<br/>AppMarketplace<br/>Integration]
    end

    subgraph "Worker"
        direction TB
        ParseWF[ParseWorkflow]
        PyPIParseWF[PyPIParseWorkflow]
        GenerateWF[GenerateWorkflow]
        PublishWF[PublishWorkflow]

        CloneAct[clone_repo_activity]
        ParseAct[parse_routes_activity]
        AuthDetect[detect_auth_activity]
        FetchPyPI[fetch_pypi_sdist_activity]
        GenAct[generate_packages_activity]
        ZipAct[package_zip_activity]
        UploadAct[upload_artifact_activity]
        PublishAct[publish_to_pypi_activity]
        StatusAct[update_service_status]
        CleanupAct[cleanup_clone_activity]
    end

    subgraph "CLI Library (src/genalphacli)"
        direction TB
        Pipeline[Pipeline<br/>run_pipeline]
        FastAPIParsers[FastAPI Parser<br/>AST extraction]
        OpenAPIParsers[OpenAPI Parser<br/>spec parsing]
        ConfigDetector[Config Detector<br/>auth + base_url]
        PipGen[Pip Generator<br/>CLI templates]
        MCPGen[MCP Generator<br/>MCP templates]
        Models[Models<br/>CommandGraph, AuthConfig<br/>Subcommand, RouteParam]
        PyPIClient[PyPI Client<br/>fetch, download, extract]
        GitHubClient[GitHub Client<br/>clone, detect framework]
    end
```

## Database Schema (ERD)

```mermaid
erDiagram
    core_users {
        string id PK
        string email UK
        string name
        boolean email_verified
        datetime created_at
    }

    core_sessions {
        string session_id PK
        string user_id FK
        datetime expires_at
        datetime last_active_at
        string user_agent
    }

    core_workspaces {
        string id PK
        string name
        string slug UK
        string owner_id FK
        string integration_id
        datetime created_at
    }

    core_workspace_members {
        string id PK
        string workspace_id FK
        string user_id FK
        string role
        datetime created_at
    }

    core_projects {
        string id PK
        string workspace_id FK
        string name
        string description
        datetime created_at
    }

    core_services {
        string id PK
        string project_id FK
        string name
        string repo_url
        string source_type
        string source_version
        string framework
        string status
        json route_graph
        string error_message
        string parse_workflow_id
        string generate_workflow_id
        string artifact_id
        json metadata_json
        datetime created_at
        datetime updated_at
    }

    core_artifacts {
        string id PK
        string service_id FK
        string artifact_type
        string filename
        binary file_data
        int file_size
        datetime created_at
    }

    tps_app_marketplace {
        string id PK
        int app_code UK
        string app_name UK
        string display_name
        int auth_type
        int category
        int provider
        json meta
        boolean is_install_required
        boolean active
    }

    tps_integrations {
        string id PK
        string user_id
        string app_id FK
        string app_name
        string config_encrypted
        string status
        string identifier
        float expires_at
    }

    core_users ||--o{ core_sessions : has
    core_users ||--o{ core_workspaces : owns
    core_users ||--o{ core_workspace_members : member_of
    core_workspaces ||--o{ core_workspace_members : has
    core_workspaces ||--o{ core_projects : contains
    core_projects ||--o{ core_services : contains
    core_services ||--o{ core_artifacts : has
    tps_app_marketplace ||--o{ tps_integrations : installed_as
```

## Workflow Diagrams

### Parse Flow (GitHub)

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant C as Core
    participant T as Temporal
    participant W as Worker
    participant GH as GitHub
    participant TPS as TPS

    U->>F: Paste GitHub URL
    F->>C: POST /parse {repoUrl, projectId}
    C->>C: Validate URL, create Service(status=cloning)
    C->>TPS: GET /integrations (find GitHub token)
    C->>T: Start ParseWorkflow
    C-->>F: {serviceId, workflowId, status: cloning}

    T->>W: Execute clone_repo_activity
    W->>TPS: GET /integrations/{id}/token
    TPS-->>W: {access_token}
    W->>GH: git clone (authenticated)
    W->>C: POST /services/{id}/status {status: cloning}

    T->>W: Execute parse_routes_activity
    W->>W: FastAPI parser + OpenAPI parser
    W->>W: detect_framework, merge_routes
    W->>C: POST /services/{id}/status {status: parsing}

    T->>W: Execute detect_auth_activity
    W->>W: Filter POST routes with credential params
    W-->>W: auth_candidates[]

    T->>W: Execute update_service_status
    W->>C: POST /services/{id}/status {status: parsed, route_graph, auth_candidates}

    F->>F: Poll service status → show route mindmap
    F->>F: Show auth config modal
    U->>F: Confirm login endpoint
    F->>C: POST /services/{id}/auth-config
```

### Generate + Publish Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant C as Core
    participant T as Temporal
    participant W as Worker
    participant PP as PyPI

    U->>F: Click Generate (or Publish)
    F->>C: POST /generate (or /publish)
    C->>T: Start GenerateWorkflow (or PublishWorkflow)

    T->>W: Execute generate_packages_activity
    W->>W: Jinja2 templates → CLI + MCP packages
    Note over W: pyproject.toml, cli.py, client.py,<br/>auth.py, server.py

    alt Generate Only
        T->>W: Execute package_zip_activity
        W->>W: ZIP the output directory
        T->>W: Execute upload_artifact_activity
        W->>C: POST /services/{id}/artifacts (multipart)
        C->>C: Store in core_artifacts (binary)
        U->>F: Download ZIP
    else Publish to PyPI
        T->>W: Execute publish_to_pypi_activity
        W->>W: python -m build (sdist + wheel)
        W->>C: GET TPS token via /integrations/{id}/token
        W->>PP: PUT upload.pypi.org/legacy/ (per package)
        W->>C: POST /services/{id}/status {published_packages}
        F->>F: Show PyPI URLs
    end
```

### Auth Flow (Magic Link)

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant C as Core
    participant R as Resend
    participant DB as Core DB

    U->>F: Enter email
    F->>C: POST /auth/magic-link {email}
    C->>C: Generate signed token (itsdangerous)
    C->>R: Send email with link
    C-->>F: {message: "Link sent"}

    U->>U: Click link in email
    U->>F: GET /auth/verify?token=xxx
    F->>C: GET /auth/verify?token=xxx
    C->>C: Verify token signature + expiry
    C->>DB: Find/create User
    C->>DB: Create Workspace (if new)
    C->>DB: Create Session
    C-->>F: Set-Cookie: session_id=xxx
    F->>F: Redirect to dashboard
```

### OAuth Integration Flow (GitHub)

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant C as Core
    participant TPS as TPS
    participant GH as GitHub

    U->>F: Click "Connect GitHub"
    F->>C: POST /integrations/github/install
    C->>C: Generate encrypted state blob
    C->>TPS: POST /integrations/github/install {state, redirect_uri}
    TPS->>TPS: Build GitHub authorize URL
    TPS-->>C: {authorize_url}
    C-->>F: {authorize_url}
    F->>GH: Redirect to GitHub OAuth

    U->>GH: Authorize app
    GH->>C: GET /oauth/callback?code=xxx&state=xxx
    C->>C: Decrypt + validate state
    C->>TPS: POST /integrations/github/exchange {code, redirect_uri}
    TPS->>GH: POST /login/oauth/access_token
    GH-->>TPS: {access_token, scope}
    TPS->>GH: GET /user (fetch username)
    TPS->>TPS: Encrypt + store integration
    TPS-->>C: {integration_id, identifier}
    C-->>F: Redirect to App Store (connected!)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, React Query |
| Core API | Python, FastAPI, SQLModel, asyncpg |
| TPS API | Python, FastAPI, SQLModel, asyncpg, MultiFernet |
| Worker | Python, Temporal SDK, httpx |
| CLI Library | Python, Jinja2 (sandboxed), AST parsing |
| Database | PostgreSQL 18 (dual: core + tps) |
| Orchestration | Temporal (workflows + activities) |
| Infrastructure | Docker Compose (Postgres + Temporal + Temporal UI) |
| Email | Resend API |
| Auth | Magic link (itsdangerous) + session cookies |
| Generated CLI | Python, typer, requests |
| Generated MCP | Python, fastmcp, httpx |
