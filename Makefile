SHELL := /bin/bash
.PHONY: install test verify serve health-check frontend-install frontend-build frontend-test dev

# NOTE: verify/serve/risk-check are run from the repo root (not backend/) —
# config and dist paths in helio.config / risk.checks are repo-root-relative.

install:
	cd backend && pip install -e ".[dev]"

test:
	cd backend && pytest

verify:
	source backend/.venv/bin/activate && python -m helio.cli.main verify

serve:
	source backend/.venv/bin/activate && python -m helio.cli.main serve

health-check:
	python3 scripts/health_check.py

frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && npm run build

frontend-test:
	cd frontend && npm test

dev:
	bash scripts/dev_up.sh
