UV := uv run
# Also update TIKA_VERSION in src/tikara/util/java.py to match
TIKA_VERSION := 3.2.3
TIKA_JAR := src/tikara/jars/tika-app-$(TIKA_VERSION).jar

.DEFAULT_GOAL := help

# ── Help ──────────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help message
	@echo "tikara — python wrapper for apache tika"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; section=""} \
		/^## / { section=substr($$0, 4); printf "\n\033[1m%s\033[0m\n", section } \
		/^[a-zA-Z_-]+:.*##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────────────────

## Setup

.PHONY: install
install: ## Install all dependencies (including dev)
	uv sync --all-groups

.PHONY: download-tika
download-tika: ## Download the Tika app JAR (set TIKA_VERSION to override)
	@mkdir -p src/tikara/jars
	@echo "Downloading tika-app-$(TIKA_VERSION).jar..."
	@curl -fL -o "$(TIKA_JAR)" \
		"https://repo1.maven.org/maven2/org/apache/tika/tika-app/$(TIKA_VERSION)/tika-app-$(TIKA_VERSION).jar"
	@echo "Saved to $(TIKA_JAR)"

.PHONY: stubs
stubs: ## Regenerate Java type stubs from the Tika JAR
	@$(UV) python -m stubgenj \
		--classpath "$(TIKA_JAR)" \
		--convert-strings \
		org.apache.tika java org.apache.commons org.w3c.dom org.xml.sax \
		javax.xml javax.accessibility javax.crypto org.apache.poi \
		--output-dir stubs --no-stubs-suffix
	@rm -rf stubs/jpype-stubs

# ── Lint & Format ─────────────────────────────────────────────────────────────

## Lint & Format

.PHONY: lint
lint: ## Run ruff linter (with auto-fix)
	@$(UV) ruff check . --fix

.PHONY: format
format: ## Run ruff formatter
	@$(UV) ruff format .

.PHONY: ruff
ruff: lint format ## Run linter and formatter together

# ── Test ──────────────────────────────────────────────────────────────────────

## Test

.PHONY: test
test: ## Run tests with verbose output
	@$(UV) python -m pytest -vv -s

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report (XML + terminal)
	@$(UV) python -m pytest \
		--junitxml=junit.xml \
		--cov-report term \
		--cov-report xml:coverage.xml \
		--cov=tikara

.PHONY: test-fast
test-fast: ## Run tests, skip slow benchmark/isolated markers
	@$(UV) python -m pytest -vv -s -m "not benchmark and not isolated"

# ── Security ──────────────────────────────────────────────────────────────────

## Security

.PHONY: safety
safety: ## Run safety dependency vulnerability scan
	@$(UV) safety scan --save-as html safety_scan.html

# ── Docs ──────────────────────────────────────────────────────────────────────

## Docs

.PHONY: docs
docs: ## Build Sphinx HTML docs
	@$(UV) pydocstyle src
	@$(UV) sphinx-apidoc -f -o docs/source/ . "test*"
	@$(UV) sphinx-build -b html docs/source/ docs/build/html

.PHONY: docs-open
docs-open: docs ## Build docs and open in browser
	@xdg-open docs/build/html/index.html 2>/dev/null || open docs/build/html/index.html

# ── Build & Release ───────────────────────────────────────────────────────────

## Build & Release

.PHONY: build
build: ## Build sdist and wheel
	uv build

.PHONY: clean
clean: ## Remove build artifacts, caches, and generated reports
	@rm -rf dist/ build/ .eggs/ *.egg-info
	@rm -rf docs/build/
	@rm -rf .pytest_cache/ .ruff_cache/ .coverage htmlcov/
	@rm -f junit.xml coverage.xml safety_scan.html
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
	@find . -name "*.pyc" -delete 2>/dev/null; true
	@echo "Clean."

# ── CI / Pre-push ─────────────────────────────────────────────────────────────

## CI / Pre-push

.PHONY: ci
ci: ruff test-coverage safety docs ## Run full CI suite (lint → test → safety → docs)

.PHONY: prepush
prepush: ci ## Alias for ci — run before pushing
