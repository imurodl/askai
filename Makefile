.PHONY: dev run web up down logs db install test lint format clean embed build

# =============================================================================
# Development
# =============================================================================

# Backend with hot reload (excludes heavy directories)
dev:
	.venv/bin/uvicorn src.app.api.main:app --reload \
		--reload-exclude '.venv' \
		--reload-exclude '.git' \
		--reload-exclude '__pycache__' \
		--reload-exclude '*.pyc' \
		--port 8000

# Backend without reload (production-like)
run:
	.venv/bin/uvicorn src.app.api.main:app --port 8000

# Frontend dev server
web:
	cd web && npm run dev

# Frontend production build
build:
	cd web && npm run build

# =============================================================================
# Docker
# =============================================================================

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

# =============================================================================
# Database
# =============================================================================

db:
	docker compose exec db psql -U postgres -d askai

# Run embedding generation
embed:
	.venv/bin/python -m src.app.rag.embeddings

# =============================================================================
# Dependencies
# =============================================================================

install:
	pip install -e .
	cd web && npm install

# =============================================================================
# Code Quality
# =============================================================================

lint:
	.venv/bin/ruff check src/

format:
	.venv/bin/ruff format src/

test:
	.venv/bin/pytest tests/ -v

# =============================================================================
# Cleanup
# =============================================================================

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
