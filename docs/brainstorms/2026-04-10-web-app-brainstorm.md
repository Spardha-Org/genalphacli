---
date: 2026-04-10
topic: web-app
---

# GenAlpha CLI Web App

## What We're Building

A multi-tenant developer SaaS platform that starts with genalphacli's core capability: paste a GitHub repo URL, parse API routes via static analysis, and download generated CLI tools and MCP servers — all through the browser.

**The bigger vision:** A platform that eliminates "context debt" for development teams. Beyond CLI/MCP generation, the roadmap includes SDK generation, compound engineering skill authoring and distribution, and org-customized coding assistants (like Claude Code but fully context-aware for a specific organization). New devs become productive immediately because the platform understands the org's codebase.

**MVP scope:** Parse + Visualize + Download. User pastes a GitHub URL → sees parsed routes with live progress → reviews a visual mindmap of the API graph (routes grouped by resource, showing CLI commands and MCP tools) → configures output → downloads CLI/MCP packages as a zip.

## Why This Approach

We considered four architecture patterns for the Next.js ↔ Python communication:

1. **Queue-based (Celery + Redis)** — Simple but fragile multi-step chains, basic retries, no per-step resume.
2. **Temporal durable workflows** — Production-grade orchestration, per-step resume, built-in visibility UI. More complex but scales with the platform.
3. **Direct HTTP** — Simplest but blocks on long-running parses, timeout risks.
4. **Serverless functions** — Zero ops but cold starts, packaging pain, awkward for git clones.

**Chose Temporal from day one.** The pipeline (Clone → Parse → Generate → Package → Deliver) is inherently multi-step, each step is expensive, and the platform will grow into more complex orchestration (parallel parsing, human-in-the-loop approval, webhook flows). Temporal's durable execution model means if step 3 crashes, it resumes from step 3 — not re-clone the repo. The built-in Web UI gives instant visibility into every user's pipeline status. Companies like Replit and Lovable use Temporal for similar developer tooling pipelines.

The learning curve is real (1-2 weeks for the deterministic workflow model), but the investment pays off as the platform scales to multi-tenant workloads.

## Key Decisions

- **MVP scope**: Parse + Download (no dashboard, no team features yet)
- **Auth**: GitHub OAuth for UI (doubles as repo access token) + API keys for programmatic/CI access. All parsing requires authentication — no anonymous access.
- **Frontend**: Next.js + React
- **Backend**: Next.js API routes (web layer, Temporal TypeScript SDK client) + Python Temporal workers (heavy lifting, Temporal Python SDK)
- **Orchestration**: Temporal workflows — each generation is a durable workflow with 5 activity steps. Next.js starts/queries workflows via the Temporal TS SDK; Python workers execute activities.
- **Temporal hosting**: Docker Compose locally for dev, Cloud vs self-hosted decided at deploy time
- **Database**: PostgreSQL (user accounts, parse history, API keys)
- **Package delivery**: Zip download
- **Deployment hosting**: Decide later — containerize everything for portability
- **Repo structure**: Monorepo — `web/` directory in existing genalphacli repo
- **UX**: Live progress steps (Cloning... ✓ → Parsing... ✓ → Generating... ✓ → Download ready!) via SSE/WebSocket from Temporal workflow status. After parsing, show an interactive mindmap visualization of the API graph — routes grouped by resource, with CLI command names and MCP tool names as nodes. User reviews the graph before triggering generation.
- **Data model**: Workspace (account) → Project (collection) → Service (parsed repo + outputs). MVP: 1 workspace/user, 2 services/workspace
- **Storage**: graph.json in Postgres JSONB, zips on local disk (S3 later)
- **Repo limits**: 500MB max, 5 minute parse timeout
- **Existing code reuse**: Pipeline, parsers, generators, and models are fully reusable — they accept `Path` objects and return Pydantic models with zero CLI coupling. The Python Temporal worker wraps existing functions as activities.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  NEXT.JS (web/)                                              │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ React UI │  │ API Routes   │  │ Auth (GitHub OAuth)    │ │
│  │ (pages)  │──│ /api/parse   │──│ + API key management   │ │
│  │          │  │ /api/status  │  │                        │ │
│  └──────────┘  │ /api/download│  └────────────────────────┘ │
│                └──────┬───────┘                              │
└───────────────────────┼─────────────────────────────────────┘
                        │ Start workflow / Query status
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  TEMPORAL SERVER (Docker Compose locally)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ GeneratePipelineWorkflow                              │   │
│  │  1. clone_repo (activity)                             │   │
│  │  2. parse_routes (activity)     ← run_pipeline()      │   │
│  │  3. generate_packages (activity) ← pip/mcp generators │   │
│  │  4. package_zip (activity)                            │   │
│  │  5. finalize (activity)         → update DB, notify   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                        │
┌───────────────────────┼─────────────────────────────────────┐
│  PYTHON WORKERS (src/genalphacli/ — existing code!)          │
│  ┌────────────┐ ┌──────────┐ ┌───────────┐ ┌────────────┐  │
│  │ pipeline.py│ │ parsers/ │ │generators/│ │ github.py  │  │
│  │            │ │ openapi  │ │ pip_gen   │ │ clone/     │  │
│  │run_pipeline│ │ fastapi  │ │ mcp_gen   │ │ detect     │  │
│  └────────────┘ └──────────┘ └───────────┘ └────────────┘  │
└─────────────────────────────────────────────────────────────┘
                        │
                ┌───────┴───────┐
                │  PostgreSQL   │
                │  - users      │
                │  - workspaces │
                │  - projects   │
                │  - services   │
                │  - api_keys   │
                │  - graphs     │
                └───────────────┘
```

## Resolved Questions

- **Multi-tenancy model**: Workspace → Project → Service hierarchy. Workspace = user account, Project = collection of related APIs, Service = one parsed repo + its outputs. MVP: 1 workspace per user, max 2 services per workspace.
- **Storage**: graph.json in Postgres JSONB column. Generated zips on local disk (migrate to S3 later).
- **Repo limits**: Max 500MB repo size, 5 minute parse timeout. Temporal handles timeout gracefully.

## Open Questions

- **Pricing model**: Free tier limits? What triggers paid plans? (Deferred — figure out after MVP validation.)

## Next Steps

→ `/workflows:plan` for implementation details
