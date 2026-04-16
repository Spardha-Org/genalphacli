# Contributing to GenAlpha

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Getting Started

1. Fork and clone the repo
2. Copy environment files:
   ```bash
   cp .env.example .env
   cp web/.env.example web/.env
   ```
3. Start infrastructure and services:
   ```bash
   make dev
   ```
4. Open http://localhost:3000

### Running Tests

```bash
# All parser tests
.venv/bin/python -m pytest tests/parsers/ -v

# Full test suite
.venv/bin/python -m pytest -v
```

## Making Changes

1. Create a branch from `main`:
   ```bash
   git checkout -b feat/your-feature
   ```
2. Make your changes
3. Run tests and make sure they pass
4. Push and open a PR against `main`

### Branch Naming

- `feat/` — new features
- `fix/` — bug fixes
- `docs/` — documentation
- `chore/` — maintenance tasks
- `refactor/` — code refactoring

### Commit Messages

Use conventional commits:
- `feat: add Django parser`
- `fix: resolve include() path resolution`
- `docs: update setup instructions`
- `test: add edge case tests`

## Pull Requests

- All PRs require 1 approval before merging
- Only squash merges are allowed
- Keep PRs focused — one feature/fix per PR
- Include a clear description of what changed and why
- Add tests for new functionality

## Project Structure

```
src/genalphacli/       # Core library — parsers, generators, pipeline
services/core/         # Core API service (FastAPI)
services/tps/          # Third-party service proxy
worker/                # Temporal worker for async jobs
web/                   # Next.js frontend
infra/                 # Terraform + Docker infrastructure
tests/                 # Test suite
```

## Where to Contribute

- **Add a new framework parser** — see `src/genalphacli/parsers/` for examples (FastAPI, Django)
- **Improve route extraction** — better parameter detection, response model resolution
- **Frontend improvements** — UI/UX at `web/`
- **Documentation** — always welcome

## Questions?

Open an issue or start a discussion. We're happy to help!
