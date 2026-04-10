.PHONY: infra core tps worker web dev stop logs clean help

# ── Configuration ──
SHELL := /bin/bash
ENV_FILE := .env

# Colors
GREEN  := \033[0;32m
YELLOW := \033[0;33m
CYAN   := \033[0;36m
NC     := \033[0m

# ── Help ──
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(CYAN)%-15s$(NC) %s\n", $$1, $$2}'

# ── Infrastructure ──
infra: ## Start PostgreSQL + Temporal + Temporal UI (Docker)
	@echo "$(GREEN)Starting infrastructure...$(NC)"
	docker compose up -d
	@echo "$(GREEN)Waiting for Postgres to be healthy...$(NC)"
	@until docker compose exec -T postgres pg_isready -U genalpha > /dev/null 2>&1; do sleep 1; done
	@echo "$(GREEN)Infrastructure ready$(NC)"
	@echo "  Postgres:    localhost:5432"
	@echo "  Temporal:    localhost:7233"
	@echo "  Temporal UI: http://localhost:8080"

# ── Backend Services ──
core: ## Start Core service (:8000)
	@echo "$(GREEN)Starting Core service on :8000...$(NC)"
	set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run uvicorn services.core.main:app --port 8000 --reload --log-level info

tps: ## Start TPS service (:8001)
	@echo "$(GREEN)Starting TPS service on :8001...$(NC)"
	set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run uvicorn services.tps.main:app --port 8001 --reload --log-level info

worker: ## Start Temporal worker
	@echo "$(GREEN)Starting Temporal worker...$(NC)"
	set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run python -m worker.worker

# ── Frontend ──
web: ## Start Next.js frontend (:3000)
	@echo "$(GREEN)Starting Next.js on :3000...$(NC)"
	cd web && npm run dev

# ── All-in-One ──
dev: infra ## Start everything (infra + core + tps + web) in background
	@echo "$(GREEN)Starting all services...$(NC)"
	@mkdir -p .logs
	@# Start Core in background
	@set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run uvicorn services.core.main:app --port 8000 --reload --log-level info \
		> .logs/core.log 2>&1 & echo $$! > .pids/core.pid
	@# Start TPS in background
	@set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run uvicorn services.tps.main:app --port 8001 --reload --log-level info \
		> .logs/tps.log 2>&1 & echo $$! > .pids/tps.pid
	@# Start Next.js in background
	@cd web && npm run dev > ../.logs/web.log 2>&1 & echo $$! > .pids/web.pid
	@sleep 3
	@echo ""
	@echo "$(GREEN)All services started!$(NC)"
	@echo "  $(CYAN)Frontend:$(NC)    http://localhost:3000"
	@echo "  $(CYAN)Core API:$(NC)    http://localhost:8000/docs"
	@echo "  $(CYAN)TPS API:$(NC)     http://localhost:8001/docs"
	@echo "  $(CYAN)Temporal UI:$(NC) http://localhost:8080"
	@echo ""
	@echo "  Logs: $(YELLOW)make logs$(NC)"
	@echo "  Stop: $(YELLOW)make stop$(NC)"

# ── Lifecycle ──
stop: ## Stop all background services
	@echo "$(YELLOW)Stopping services...$(NC)"
	@-kill $$(cat .pids/core.pid 2>/dev/null) 2>/dev/null; rm -f .pids/core.pid
	@-kill $$(cat .pids/tps.pid 2>/dev/null) 2>/dev/null; rm -f .pids/tps.pid
	@-kill $$(cat .pids/web.pid 2>/dev/null) 2>/dev/null; rm -f .pids/web.pid
	@# Also kill by port in case services were started outside make
	@-lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
	@-lsof -ti:8001 2>/dev/null | xargs kill -9 2>/dev/null || true
	@-lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null || true
	@-lsof -ti:3001 2>/dev/null | xargs kill -9 2>/dev/null || true
	@docker compose stop 2>/dev/null || true
	@rm -f .logs/*.log
	@echo "$(GREEN)All services stopped$(NC)"

logs: ## Tail all service logs
	@echo "$(CYAN)=== Core ===$(NC)" && tail -20 .logs/core.log 2>/dev/null || echo "(not running)"
	@echo ""
	@echo "$(CYAN)=== TPS ===$(NC)" && tail -20 .logs/tps.log 2>/dev/null || echo "(not running)"
	@echo ""
	@echo "$(CYAN)=== Web ===$(NC)" && tail -20 .logs/web.log 2>/dev/null || echo "(not running)"

logs-core: ## Tail Core service logs
	@tail -f .logs/core.log

logs-tps: ## Tail TPS service logs
	@tail -f .logs/tps.log

logs-web: ## Tail Next.js logs
	@tail -f .logs/web.log

# ── Testing ──
test: ## Run all Python tests
	uv run pytest -v

lint: ## Run ruff linter
	uv run ruff check src/ tests/ services/ worker/

# ── Utilities ──
setup: ## First-time setup: install deps, start infra, run migrations
	@echo "$(GREEN)Installing dependencies...$(NC)"
	uv sync --group services --group worker --group dev
	@echo "$(GREEN)Installing frontend deps...$(NC)"
	cd web && npm install
	@echo "$(GREEN)Starting infrastructure...$(NC)"
	$(MAKE) infra
	@echo ""
	@echo "$(GREEN)Setup complete!$(NC)"
	@echo "  1. Fill in TPS_GITHUB_CLIENT_SECRET in .env"
	@echo "  2. Run: $(CYAN)make dev$(NC)"

clean: ## Remove logs, pids, and stop Docker
	@rm -rf .logs .pids
	@docker compose down -v 2>/dev/null || true
	@echo "$(GREEN)Cleaned up$(NC)"

# Create dirs on first run
$(shell mkdir -p .pids .logs)
