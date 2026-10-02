AGENTS_DIR := src
AGENT_DIR := $(AGENTS_DIR)/adk_01_pit_wall
EVAL_RUN := uv run --group eval adk eval $(AGENT_DIR) --print_detailed_results

.PHONY: help sync install hooks hooks-run run web api eval test lint lint-fix format format-check audit ci check clean

help: ## Lists all available Makefile commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

sync: ## Installs runtime and dev dependencies using uv
	uv sync

install: sync ## Alias for sync

hooks: ## Installs the pre-commit hooks into .git/hooks
	uv run pre-commit install

hooks-run: ## Runs all pre-commit hooks against all files
	uv run pre-commit run --all-files

run: ## Chats with the agent in the terminal
	uv run adk run $(AGENT_DIR)

web: ## Starts the ADK dev UI on localhost
	uv run adk web $(AGENTS_DIR)

api: ## Starts the ADK API server on localhost
	uv run adk api_server $(AGENTS_DIR)

eval: ## Runs the eval sets against Gemini and Jolpica (requires credentials)
	$(EVAL_RUN) evals/pit_wall.evalset.json --config_file_path evals/test_config.json
	$(EVAL_RUN) evals/pit_wall_guardrails.evalset.json --config_file_path evals/guardrails_config.json

test: ## Runs the test suite with pytest
	uv run pytest

lint: ## Checks code with ruff
	uv run ruff check .

lint-fix: ## Automatically fixes ruff lint issues
	uv run ruff check --fix .

format: ## Formats code with ruff
	uv run ruff format .

format-check: ## Verifies formatting with ruff without modifying files
	uv run ruff format --check .

# Both advisories come only from the eval group and never run in the agent:
# PYSEC-2026-3740: unpatched NLTK sandbox bypass, pulled via rouge-score
# PYSEC-2026-4066: SSRF in the LiteLLM proxy server; google-cloud-aiplatform[evaluation] pins litellm<1.86 on Python <3.14
PIP_AUDIT_IGNORE := --ignore-vuln PYSEC-2026-3740 --ignore-vuln PYSEC-2026-4066

audit: ## Audits dependencies for known security vulnerabilities
	uv run pip-audit $(PIP_AUDIT_IGNORE)

ci: lint format-check audit test ## Runs full verification pipeline locally

check: ci ## Alias for ci

clean: ## Cleans build artifacts and caches
	rm -rf .ruff_cache .pytest_cache dist build *.egg-info .coverage htmlcov
	find . -type d -name '__pycache__' -not -path './.venv*' -exec rm -rf {} +
