# Makefile for MCP Markdown Server
# This Makefile provides common development tasks for the MCP markdown server

.PHONY: help install setup setup-dev clean test test-unit test-integration test-coverage lint lint-ruff lint-mypy lint-bandit format format-check run dev check ci pre-commit deps-check venv activate

# Default target
help: ## Show this help message
	@echo "MCP Markdown Server - Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

# Variables
PYTHON := python3
PIP := pip
VENV := venv
VENV_BIN := $(VENV)/bin
PYTHON_VENV := $(VENV_BIN)/python
PIP_VENV := $(VENV_BIN)/pip
SERVER_FILE := server.py
HOST := localhost
PORT := 8000
TRANSPORT := http

# Setup and Installation
venv: ## Create virtual environment
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created in $(VENV)/"

install: venv ## Install dependencies in virtual environment
	@echo "Installing dependencies..."
	$(PIP_VENV) install --upgrade pip
	$(PIP_VENV) install -r requirements.txt
	@echo "✅ Dependencies installed successfully!"

setup: install ## Complete setup (alias for install)
	@echo "✅ Setup completed!"

setup-dev: install ## Setup development environment with pre-commit hooks
	@echo "Setting up development environment..."
	$(PIP_VENV) install pre-commit
	$(VENV_BIN)/pre-commit install
	@echo "Running pre-commit on all files..."
	$(VENV_BIN)/pre-commit run --all-files || true
	@echo "✅ Development environment setup complete!"
	@echo "Pre-commit hooks are now installed and will run automatically on git commits."

deps-check: ## Check if all dependencies are installed
	@echo "Checking dependencies..."
	@$(PYTHON_VENV) -c "import fastmcp, googleapiclient, google.oauth2" && \
		echo "✅ All dependencies are installed" || \
		(echo "❌ Dependencies missing. Run 'make install'" && exit 1)

# Development
run: deps-check ## Run the MCP server (default: http://localhost:8000)
	@echo "Starting MCP Markdown Server..."
	@echo "Server will run on $(TRANSPORT)://$(HOST):$(PORT)"
	@echo "Endpoint: http://$(HOST):$(PORT)/mcp"
	@echo "Press Ctrl+C to stop"
	@$(PYTHON_VENV) $(SERVER_FILE)

# Testing
test: deps-check ## Run all tests
	@echo "Running all tests..."
	$(VENV_BIN)/pytest

test-unit: deps-check ## Run unit tests only
	@echo "Running unit tests..."
	$(VENV_BIN)/pytest -m "unit or not integration"

test-integration: deps-check ## Run integration tests only
	@echo "Running integration tests..."
	$(VENV_BIN)/pytest -m integration

test-verbose: deps-check ## Run tests with verbose output
	@echo "Running tests with verbose output..."
	$(VENV_BIN)/pytest -v -s

test-coverage: deps-check ## Run tests with coverage report
	@echo "Running tests with coverage..."
	$(PIP_VENV) install pytest-cov
	$(VENV_BIN)/pytest --cov=. --cov-report=xml --cov-report=term

# Code Quality
lint-ruff: deps-check ## Run ruff linting checks
	@echo "Running ruff checks..."
	$(VENV_BIN)/ruff check . --fix

lint-mypy: deps-check ## Run mypy type checking
	@echo "Running mypy type checks..."
	$(VENV_BIN)/mypy .

lint-bandit: deps-check ## Run bandit security checks
	@echo "Running bandit security checks..."
	$(VENV_BIN)/bandit -r server.py test_bearer_token.py -f json --skip B101,B105

lint: lint-ruff lint-mypy lint-bandit ## Run all linting checks (ruff, mypy, bandit)
	@echo "✅ All linting checks passed!"

format: deps-check ## Format code with ruff
	@echo "Formatting code with ruff..."
	$(VENV_BIN)/ruff format .

format-check: deps-check ## Check code formatting without making changes
	@echo "Checking code formatting with ruff..."
	$(VENV_BIN)/ruff format --check .

check: deps-check lint format-check test ## Run all checks (lint, format, test)
	@echo "✅ All checks passed!"

ci: deps-check lint format-check test-coverage ## Run all CI checks (comprehensive)
	@echo "✅ All CI checks passed!"

pre-commit: deps-check ## Run pre-commit on all files
	@echo "Running pre-commit on all files..."
	$(PIP_VENV) install pre-commit
	$(VENV_BIN)/pre-commit install
	$(VENV_BIN)/pre-commit run --all-files

# Utility
clean: ## Clean up generated files and caches
	@echo "Cleaning up..."
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf *.pyc
	rm -rf .mypy_cache/
	@echo "✅ Cleanup completed!"

clean-all: clean ## Clean everything including virtual environment
	@echo "Removing virtual environment..."
	rm -rf $(VENV)/
	@echo "✅ Complete cleanup finished!"

activate: ## Show command to activate virtual environment
	@echo "To activate the virtual environment, run:"
	@echo "  source $(VENV_BIN)/activate"

info: ## Show project information
	@echo "MCP Markdown Server Project Information:"
	@echo "  Python: $(shell $(PYTHON) --version 2>/dev/null || echo 'Not found')"
	@echo "  Virtual env: $(VENV)/"
	@echo "  Server file: $(SERVER_FILE)"
	@echo "  Default endpoint: http://$(HOST):$(PORT)/mcp"
	@echo ""
	@echo "Available environment variables:"
	@echo "  HOST (default: $(HOST))"
	@echo "  PORT (default: $(PORT))"
	@echo "  TRANSPORT (default: $(TRANSPORT))"
	@echo "  LOG_LEVEL (default: INFO)"

# Docker-related (if you want to add Docker support later)
docker-build: ## Build Docker image
	@echo "Building Docker image..."
	docker build -t mcp-markdown-server .

docker-run: ## Run Docker container
	@echo "Running Docker container..."
	docker run -p $(PORT):$(PORT) mcp-markdown-server

# Requirements management
freeze: deps-check ## Freeze current dependencies to requirements.txt
	@echo "Freezing dependencies..."
	$(PIP_VENV) freeze > requirements-frozen.txt
	@echo "✅ Dependencies frozen to requirements-frozen.txt"

upgrade: ## Upgrade all dependencies
	@echo "Upgrading dependencies..."
	$(PIP_VENV) install --upgrade -r requirements.txt
	@echo "✅ Dependencies upgraded!"


logs: ## Show recent server logs (if running in background)
	@echo "Recent server activity:"
	@tail -f /tmp/mcp-server.log 2>/dev/null || echo "No log file found. Server might not be running in background."

# Quick start
quick-start: install run ## Quick start: install dependencies and run server

.DEFAULT_GOAL := help
