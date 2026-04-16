# GenAlpha

**Author:** Nandish Naik

Convert any API repository into a working CLI tool and MCP server — automatically.

Paste a GitHub repo URL, extract all API routes via static analysis, configure auth, and generate installable Python packages. Build a CLI for your terminal or an MCP server for AI agents like Claude.

**Live:** [app.genalpha.boot41.online](https://app.genalpha.boot41.online)

## How It Works

```
  PARSE                              BUILD                           USE
┌─────────────────────┐    ┌────────────────────────┐     ┌────────────────────┐
│ Clone + Detect      │    │  Generate:             │     │  CLI               │
│ OpenAPI Spec Parse  │───>│    [x] CLI tool        │────>│    myapi login     │
│ AST Route Extract   │    │    [x] MCP server      │     │    myapi list-users│
│ Auth Detection      │    │    [x] Auth lifecycle   │     │  MCP               │
└─────────────────────┘    └────────────────────────┘     │    "list all users"│
                                                          │  PyPI              │
                                                          │    pip install myapi│
                                                          └────────────────────┘
```

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │     │  Core API    │     │  TPS Service │
│   Next.js    │────>│  FastAPI     │────>│  FastAPI     │
│   Vercel     │     │  :8000       │     │  :8001       │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │              GitHub OAuth
                     ┌──────▼───────┐      PyPI Tokens
                     │   Temporal   │      npm Tokens
                     │   Worker     │
                     │  Parse/Gen/  │
                     │  Publish     │
                     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │  PostgreSQL  │
                     │  (RDS)       │
                     └──────────────┘
```

- **Core Service** — API gateway, auth (magic link + sessions), project/service CRUD, workflow orchestration
- **TPS (Third-Party Service)** — OAuth flows, encrypted credential storage for GitHub, PyPI, npm
- **Temporal Worker** — Durable workflows: ParseWorkflow, PyPIParseWorkflow, GenerateWorkflow, PublishWorkflow
- **Frontend** — Next.js app with route visualization, auth config modal, generate/publish UI

## Features

- **Two-layer parsing**: OpenAPI spec detection + Python AST route extraction
- **FastAPI support**: decorators, `include_router` prefix resolution, Pydantic models, `OAuth2PasswordRequestForm` recovery
- **Auth lifecycle**: automatic login endpoint detection, token extraction from unknown response shapes, `login`/`logout`/`refresh` commands
- **CLI generator**: Typer CLI with positional path params, body flags, `--pretty`, `--body` override, stored auth tokens
- **MCP server generator**: FastMCP with `@mcp.tool()` per route, shared `auth.json` with CLI
- **App integrations**: GitHub (OAuth), PyPI (API token), npm (access token)
- **Publish to PyPI**: One-click build + upload from the web UI
- **Security**: SandboxedEnvironment, AST safety walk, no code execution, SSRF prevention
- **Clean architecture**: Repository + Service + Controller layers with dependency injection

## Quick Start

### Prerequisites

- Python 3.10+ with [uv](https://docs.astral.sh/uv/)
- Node.js 18+ with npm
- Docker (for PostgreSQL + Temporal)

### Setup

```bash
git clone https://github.com/Spardha-Org/genalphacli.git
cd genalphacli

# First-time setup (installs all deps, starts Docker infra)
make setup

# Copy and configure environment
cp .env.example .env
# Edit .env — fill in secrets (see .env.example for descriptions)

# Start everything
make dev
```

Open [http://localhost:3000](http://localhost:3000) to use the web app.

## Make Commands

```
make help             Show all available commands
```

### Development

| Command | Description |
|---------|-------------|
| `make dev` | Start everything (infra + core + tps + worker + web) |
| `make stop` | Stop all background services |
| `make logs` | Tail all service logs (last 15 lines each) |
| `make clean` | Remove logs, pids, and stop Docker |

### Individual Services

| Command | Description |
|---------|-------------|
| `make infra` | Start PostgreSQL + Temporal + Temporal UI (Docker) |
| `make core` | Start Core service on :8000 |
| `make tps` | Start TPS service on :8001 (runs migrations first) |
| `make worker` | Start Temporal worker |
| `make web` | Start Next.js frontend on :3000 |

### Database & Code Generation

| Command | Description |
|---------|-------------|
| `make migrate` | Run all migrations (Core + TPS) |
| `make migrate-core` | Run Core Alembic migrations only |
| `make migrate-tps` | Run TPS Alembic migrations only |
| `make generate-api` | Generate Pydantic models from OpenAPI specs |

### Quality

| Command | Description |
|---------|-------------|
| `make test` | Run all Python tests |
| `make lint` | Run ruff linter |

### Setup & Utilities

| Command | Description |
|---------|-------------|
| `make setup` | First-time setup: install deps, start infra |
| `make logs-core` | Tail Core service logs (follow) |
| `make logs-tps` | Tail TPS service logs (follow) |
| `make logs-worker` | Tail Worker logs (follow) |
| `make logs-web` | Tail Next.js logs (follow) |

## Project Structure

```
genalphacli/
├── services/
│   ├── core/                  # Core API service
│   │   ├── routes/v1/         # API endpoints (/api/v1/*)
│   │   ├── services/          # Business logic layer
│   │   ├── repositories/      # Database access layer
│   │   ├── clients/           # TPS, Temporal, Email clients
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── auth/              # Magic link + session auth
│   │   └── migrations/        # Alembic migrations
│   └── tps/                   # Third-Party Service
│       ├── handlers/          # GitHub, PyPI, npm handlers
│       └── api/               # Apps + Integrations API
├── worker/
│   ├── activities/            # Temporal activities
│   └── workflows/             # Parse, Generate, Publish workflows
├── web/                       # Next.js frontend
│   └── src/
│       ├── app/               # App router pages
│       ├── components/        # React components
│       └── data/              # API client + hooks
├── infra/
│   ├── terraform/             # AWS infrastructure (EC2, RDS, VPC)
│   ├── docker/                # Dockerfiles + nginx config
│   └── compose/               # Production docker-compose files
├── docs/
│   ├── brainstorms/           # Design exploration documents
│   ├── plans/                 # Implementation plans
│   ├── architecture/          # Architecture documentation
│   ├── deployment/            # AWS deployment guide
│   └── guide/                 # User-facing documentation
├── tests/                     # Python test suite
├── Makefile                   # Development commands
├── pyproject.toml             # Python project config
└── docker-compose.yml         # Local dev infrastructure
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description |
|----------|-------------|
| `CORE_DATABASE__URL` | Core PostgreSQL connection string |
| `CORE_AUTH__MAGIC_LINK_SECRET` | Secret for magic link token signing |
| `CORE_TPS__URL` | TPS service URL (http://localhost:8001) |
| `CORE_TPS__SECRET` | Shared secret between Core and TPS |
| `TPS_DATABASE_URL` | TPS PostgreSQL connection string |
| `TPS_FERNET_KEYS` | Encryption key for stored credentials |
| `TPS_GITHUB_CLIENT_ID` | GitHub OAuth App client ID |
| `TPS_GITHUB_CLIENT_SECRET` | GitHub OAuth App client secret |
| `TEMPORAL_ADDRESS` | Temporal server address (localhost:7233) |

## Documentation

| Guide | |
|---|---|
| [Getting Started](docs/guide/getting-started.md) | Installation, first parse, first build |
| [CLI Reference](docs/guide/cli-reference.md) | All commands and flags |
| [Parsing Pipeline](docs/guide/parsing-pipeline.md) | How route extraction works |
| [CLI Generator](docs/guide/cli-generator.md) | Generated CLI features |
| [MCP Server Generator](docs/guide/mcp-server-generator.md) | Claude Desktop / Cursor setup |
| [Security](docs/guide/security.md) | Parser + generator + MCP security |
| [Development](docs/guide/development.md) | Dev setup, testing, project structure |
| [AWS Deployment](docs/deployment/aws-deployment-guide.md) | Production deployment on AWS |

## Deployment

Production runs on AWS:
- **Frontend**: Vercel ([app.genalpha.boot41.online](https://app.genalpha.boot41.online))
- **Backend**: EC2 t3.small (Core + TPS + Worker + Nginx)
- **Infrastructure**: EC2 t3.small (Temporal + Temporal UI)
- **Database**: RDS PostgreSQL
- **CI/CD**: GitHub Actions (`.github/workflows/deploy.yml`)

See [AWS Deployment Guide](docs/deployment/aws-deployment-guide.md) for details.

## Roadmap

- [x] FastAPI + OpenAPI parser pipeline
- [x] CLI generator (Typer, installable pip package)
- [x] MCP server generator (FastMCP, Claude Desktop compatible)
- [x] Auth lifecycle (login detection, token extraction, refresh)
- [x] Web platform with GitHub OAuth
- [x] PyPI publishing from web UI
- [x] npm integration
- [x] AWS deployment with Terraform
- [x] Temporal workflow orchestration with heartbeats
- [ ] Django REST Framework parser
- [ ] Express.js parser
- [ ] Spring Boot parser (tree-sitter)
- [ ] TypeScript/npm CLI package generation
- [ ] Cookie/session auth support
- [ ] Custom FastAPI Depends() resolution

## License

MIT

---

*Built with [Claude Code](https://claude.ai/claude-code)*
