.PHONY: infra core tps worker web dev stop logs clean help migrate

# ── Configuration ──
SHELL := /bin/bash
ENV_FILE := .env
LINE := ─────────────────────────────────────────────────────

# ── Help ──
help: ## Show this help
	@echo ""
	@printf "  \033[1mGenAlpha CLI\033[0m — Development Commands\n"
	@printf "  \033[2m$(LINE)\033[0m\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[0;36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── Infrastructure ──
infra: ## Start PostgreSQL + Temporal + Temporal UI (Docker)
	@echo ""
	@printf "  \033[2m$(LINE)\033[0m\n"
	@printf "  \033[1mInfrastructure\033[0m\n"
	@printf "  \033[2m$(LINE)\033[0m\n"
	@docker compose up -d 2>&1 | grep -v "^$$"
	@echo ""
	@printf "  \033[2mWaiting for Postgres"
	@until docker compose exec -T postgres pg_isready -U genalpha > /dev/null 2>&1; do printf "."; sleep 1; done
	@printf " \033[0;32mready\033[0m\n"
	@echo ""
	@printf "  \033[0;32m●\033[0m Postgres      \033[2mlocalhost:5432\033[0m\n"
	@printf "  \033[0;32m●\033[0m Temporal       \033[2mlocalhost:7233\033[0m\n"
	@printf "  \033[0;32m●\033[0m Temporal UI    \033[2mhttp://localhost:8080\033[0m\n"
	@echo ""

# ── Backend Services ──
core: ## Start Core service (:8000)
	@printf "  \033[0;32m●\033[0m Core starting on :8000...\n"
	set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run uvicorn services.core.main:app --port 8000 --reload --log-level info

migrate: ## Run TPS Alembic migrations
	@printf "  \033[0;32m●\033[0m Running TPS migrations...\n"
	@set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run alembic upgrade head
	@printf "  \033[0;32m●\033[0m Migrations applied\n"

tps: migrate ## Start TPS service (:8001)
	@printf "  \033[0;32m●\033[0m TPS starting on :8001...\n"
	set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run uvicorn services.tps.main:app --port 8001 --reload --log-level info

worker: ## Start Temporal worker
	@printf "  \033[0;32m●\033[0m Worker starting...\n"
	set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run python -m worker.worker

# ── Frontend ──
web: ## Start Next.js frontend (:3000)
	@printf "  \033[0;32m●\033[0m Next.js starting on :3000...\n"
	cd web && npm run dev

# ── All-in-One ──
dev: infra ## Start everything (infra + core + tps + worker + web)
	@printf "  \033[2m$(LINE)\033[0m\n"
	@printf "  \033[1mServices\033[0m\n"
	@printf "  \033[2m$(LINE)\033[0m\n"
	@echo ""
	@mkdir -p .logs
	@# Start Core
	@set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run uvicorn services.core.main:app --port 8000 --reload --log-level info \
		> .logs/core.log 2>&1 & echo $$! > .pids/core.pid
	@sleep 1
	@printf "  \033[0;32m●\033[0m Core API       \033[2mhttp://localhost:8000/docs\033[0m\n"
	@# Run TPS migrations
	@set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run alembic upgrade head > .logs/migrate.log 2>&1 || true
	@printf "  \033[0;32m●\033[0m TPS migrations  \033[2mapplied\033[0m\n"
	@# Start TPS
	@set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run uvicorn services.tps.main:app --port 8001 --reload --log-level info \
		> .logs/tps.log 2>&1 & echo $$! > .pids/tps.pid
	@sleep 1
	@printf "  \033[0;32m●\033[0m TPS API        \033[2mhttp://localhost:8001/docs\033[0m\n"
	@# Start Worker
	@set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run python -m worker.worker \
		> .logs/worker.log 2>&1 & echo $$! > .pids/worker.pid
	@sleep 1
	@printf "  \033[0;32m●\033[0m Worker         \033[2mparse + generate queues\033[0m\n"
	@# Start Next.js
	@cd web && npm run dev > ../.logs/web.log 2>&1 & echo $$! > .pids/web.pid
	@sleep 2
	@printf "  \033[0;32m●\033[0m Frontend       \033[2mhttp://localhost:3000\033[0m\n"
	@echo ""
	@printf "  \033[2m$(LINE)\033[0m\n"
	@echo ""
	@printf "  \033[1m\033[0;32mReady!\033[0m  Open \033[0;36mhttp://localhost:3000\033[0m\n"
	@echo ""
	@printf "  \033[2mmake logs\033[0m    View service logs\n"
	@printf "  \033[2mmake stop\033[0m    Stop everything\n"
	@echo ""

# ── Lifecycle ──
stop: ## Stop all background services
	@echo ""
	@printf "  Stopping services"
	@-kill $$(cat .pids/core.pid 2>/dev/null) 2>/dev/null; rm -f .pids/core.pid
	@-kill $$(cat .pids/tps.pid 2>/dev/null) 2>/dev/null; rm -f .pids/tps.pid
	@-kill $$(cat .pids/worker.pid 2>/dev/null) 2>/dev/null; rm -f .pids/worker.pid
	@-kill $$(cat .pids/web.pid 2>/dev/null) 2>/dev/null; rm -f .pids/web.pid
	@-lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
	@-lsof -ti:8001 2>/dev/null | xargs kill -9 2>/dev/null || true
	@-lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null || true
	@-lsof -ti:3001 2>/dev/null | xargs kill -9 2>/dev/null || true
	@docker compose stop 2>/dev/null || true
	@rm -f .logs/*.log
	@printf " \033[0;32mdone\033[0m\n\n"

logs: ## Tail all service logs
	@echo ""
	@printf "  \033[1mCore\033[0m \033[2m(last 15 lines)\033[0m\n"
	@printf "  \033[2m$(LINE)\033[0m\n"
	@tail -15 .logs/core.log 2>/dev/null || printf "  \033[2mnot running\033[0m\n"
	@echo ""
	@printf "  \033[1mTPS\033[0m \033[2m(last 15 lines)\033[0m\n"
	@printf "  \033[2m$(LINE)\033[0m\n"
	@tail -15 .logs/tps.log 2>/dev/null || printf "  \033[2mnot running\033[0m\n"
	@echo ""
	@printf "  \033[1mWorker\033[0m \033[2m(last 15 lines)\033[0m\n"
	@printf "  \033[2m$(LINE)\033[0m\n"
	@tail -15 .logs/worker.log 2>/dev/null || printf "  \033[2mnot running\033[0m\n"
	@echo ""
	@printf "  \033[1mWeb\033[0m \033[2m(last 15 lines)\033[0m\n"
	@printf "  \033[2m$(LINE)\033[0m\n"
	@tail -15 .logs/web.log 2>/dev/null || printf "  \033[2mnot running\033[0m\n"
	@echo ""

logs-core: ## Tail Core service logs
	@tail -f .logs/core.log

logs-tps: ## Tail TPS service logs
	@tail -f .logs/tps.log

logs-web: ## Tail Next.js logs
	@tail -f .logs/web.log

logs-worker: ## Tail Worker logs
	@tail -f .logs/worker.log

# ── Testing ──
test: ## Run all Python tests
	uv run pytest -v

lint: ## Run ruff linter
	uv run ruff check src/ tests/ services/ worker/

# ── Utilities ──
setup: ## First-time setup: install deps, start infra
	@echo ""
	@printf "  \033[1mGenAlpha CLI\033[0m — First Time Setup\n"
	@printf "  \033[2m$(LINE)\033[0m\n"
	@echo ""
	@printf "  \033[2mInstalling Python dependencies...\033[0m\n"
	@uv sync --group services --group worker --group dev
	@printf "  \033[0;32m●\033[0m Python deps installed\n"
	@echo ""
	@printf "  \033[2mInstalling frontend dependencies...\033[0m\n"
	@cd web && npm install
	@printf "  \033[0;32m●\033[0m Frontend deps installed\n"
	@echo ""
	$(MAKE) infra
	@printf "  \033[1m\033[0;32mSetup complete!\033[0m\n"
	@echo ""
	@printf "  Next steps:\n"
	@printf "  1. Copy \033[0;36m.env.example\033[0m to \033[0;36m.env\033[0m and fill in secrets\n"
	@printf "  2. Run \033[0;36mmake dev\033[0m\n"
	@echo ""

clean: ## Remove logs, pids, and stop Docker
	@rm -rf .logs .pids
	@docker compose down -v 2>/dev/null || true
	@printf "  \033[0;32m●\033[0m Cleaned up\n"

# Create dirs on first run
$(shell mkdir -p .pids .logs)
