.PHONY: infra core tps worker web dev stop logs clean help

# ── Configuration ──
SHELL := /bin/bash
ENV_FILE := .env

# Colors
GREEN  := \033[0;32m
YELLOW := \033[0;33m
CYAN   := \033[0;36m
DIM    := \033[2m
BOLD   := \033[1m
NC     := \033[0m

# Box drawing
LINE   := ─────────────────────────────────────────────────────

# ── Help ──
help: ## Show this help
	@echo ""
	@echo "  $(BOLD)GenAlpha CLI$(NC) — Development Commands"
	@echo "  $(DIM)$(LINE)$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ── Infrastructure ──
infra: ## Start PostgreSQL + Temporal + Temporal UI (Docker)
	@echo ""
	@echo "  $(DIM)$(LINE)$(NC)"
	@echo "  $(BOLD)Infrastructure$(NC)"
	@echo "  $(DIM)$(LINE)$(NC)"
	@docker compose up -d 2>&1 | grep -v "^$$"
	@echo ""
	@printf "  $(DIM)Waiting for Postgres"
	@until docker compose exec -T postgres pg_isready -U genalpha > /dev/null 2>&1; do printf "."; sleep 1; done
	@echo " $(GREEN)ready$(NC)"
	@echo ""
	@echo "  $(GREEN)●$(NC) Postgres      $(DIM)localhost:5432$(NC)"
	@echo "  $(GREEN)●$(NC) Temporal       $(DIM)localhost:7233$(NC)"
	@echo "  $(GREEN)●$(NC) Temporal UI    $(DIM)http://localhost:8080$(NC)"
	@echo ""

# ── Backend Services ──
core: ## Start Core service (:8000)
	@echo "  $(GREEN)●$(NC) Core starting on :8000..."
	set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run uvicorn services.core.main:app --port 8000 --reload --log-level info

tps: ## Start TPS service (:8001)
	@echo "  $(GREEN)●$(NC) TPS starting on :8001..."
	set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run uvicorn services.tps.main:app --port 8001 --reload --log-level info

worker: ## Start Temporal worker
	@echo "  $(GREEN)●$(NC) Worker starting..."
	set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run python -m worker.worker

# ── Frontend ──
web: ## Start Next.js frontend (:3000)
	@echo "  $(GREEN)●$(NC) Next.js starting on :3000..."
	cd web && npm run dev

# ── All-in-One ──
dev: infra ## Start everything (infra + core + tps + worker + web)
	@echo "  $(DIM)$(LINE)$(NC)"
	@echo "  $(BOLD)Services$(NC)"
	@echo "  $(DIM)$(LINE)$(NC)"
	@echo ""
	@mkdir -p .logs
	@# Start Core
	@set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run uvicorn services.core.main:app --port 8000 --reload --log-level info \
		> .logs/core.log 2>&1 & echo $$! > .pids/core.pid
	@sleep 1
	@printf "  $(GREEN)●$(NC) Core API       $(DIM)http://localhost:8000/docs$(NC)\n"
	@# Start TPS
	@set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run uvicorn services.tps.main:app --port 8001 --reload --log-level info \
		> .logs/tps.log 2>&1 & echo $$! > .pids/tps.pid
	@sleep 1
	@printf "  $(GREEN)●$(NC) TPS API        $(DIM)http://localhost:8001/docs$(NC)\n"
	@# Start Worker
	@set -a && source $(ENV_FILE) && set +a && \
		PYTHONPATH=.:src uv run python -m worker.worker \
		> .logs/worker.log 2>&1 & echo $$! > .pids/worker.pid
	@sleep 1
	@printf "  $(GREEN)●$(NC) Worker         $(DIM)parse + generate queues$(NC)\n"
	@# Start Next.js
	@cd web && npm run dev > ../.logs/web.log 2>&1 & echo $$! > .pids/web.pid
	@sleep 2
	@printf "  $(GREEN)●$(NC) Frontend       $(DIM)http://localhost:3000$(NC)\n"
	@echo ""
	@echo "  $(DIM)$(LINE)$(NC)"
	@echo ""
	@echo "  $(BOLD)$(GREEN)Ready!$(NC)  Open $(CYAN)http://localhost:3000$(NC)"
	@echo ""
	@echo "  $(DIM)make logs$(NC)    View service logs"
	@echo "  $(DIM)make stop$(NC)    Stop everything"
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
	@printf " $(GREEN)done$(NC)\n\n"

logs: ## Tail all service logs
	@echo ""
	@echo "  $(BOLD)Core$(NC) $(DIM)(last 15 lines)$(NC)"
	@echo "  $(DIM)$(LINE)$(NC)"
	@tail -15 .logs/core.log 2>/dev/null || echo "  $(DIM)not running$(NC)"
	@echo ""
	@echo "  $(BOLD)TPS$(NC) $(DIM)(last 15 lines)$(NC)"
	@echo "  $(DIM)$(LINE)$(NC)"
	@tail -15 .logs/tps.log 2>/dev/null || echo "  $(DIM)not running$(NC)"
	@echo ""
	@echo "  $(BOLD)Worker$(NC) $(DIM)(last 15 lines)$(NC)"
	@echo "  $(DIM)$(LINE)$(NC)"
	@tail -15 .logs/worker.log 2>/dev/null || echo "  $(DIM)not running$(NC)"
	@echo ""
	@echo "  $(BOLD)Web$(NC) $(DIM)(last 15 lines)$(NC)"
	@echo "  $(DIM)$(LINE)$(NC)"
	@tail -15 .logs/web.log 2>/dev/null || echo "  $(DIM)not running$(NC)"
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
	@echo "  $(BOLD)GenAlpha CLI$(NC) — First Time Setup"
	@echo "  $(DIM)$(LINE)$(NC)"
	@echo ""
	@echo "  $(DIM)Installing Python dependencies...$(NC)"
	@uv sync --group services --group worker --group dev
	@echo "  $(GREEN)●$(NC) Python deps installed"
	@echo ""
	@echo "  $(DIM)Installing frontend dependencies...$(NC)"
	@cd web && npm install
	@echo "  $(GREEN)●$(NC) Frontend deps installed"
	@echo ""
	$(MAKE) infra
	@echo "  $(BOLD)$(GREEN)Setup complete!$(NC)"
	@echo ""
	@echo "  Next steps:"
	@echo "  1. Copy $(CYAN).env.example$(NC) to $(CYAN).env$(NC) and fill in secrets"
	@echo "  2. Run $(CYAN)make dev$(NC)"
	@echo ""

clean: ## Remove logs, pids, and stop Docker
	@rm -rf .logs .pids
	@docker compose down -v 2>/dev/null || true
	@echo "  $(GREEN)●$(NC) Cleaned up"

# Create dirs on first run
$(shell mkdir -p .pids .logs)
