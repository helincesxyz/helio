# Contributing to Helio

Thanks for your interest in contributing! Helio is an open-source project and
contributions of all sizes are welcome — bug fixes, new strategies, better test
coverage, documentation improvements.

## Before you start

- Read [SECURITY.md](SECURITY.md) — the credential-safety rules are non-negotiable
  and reviewed on every PR.
- Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) to understand why Helio's
  backend never talks to OKX directly.

## Development setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest

cd ../frontend
npm install
npm run build
npm test
```

## Guidelines

- **No OKX network code in `backend/src/helio/`.** All OKX I/O flows through the
  Claude Code agent calling the OKX Agent Trade Kit's MCP tools. If your change
  needs new OKX data, extend the schemas/routers that Claude Code posts into —
  don't add an HTTP client.
- **Risk engine changes need tests.** `backend/src/helio/risk/` is pure,
  deterministic Python — every new rule needs unit tests covering both the
  pass and fail cases.
- **Keep the learning engine's `ParameterAdjuster` a stub** unless you're
  specifically implementing and thoroughly testing an adaptive-adjustment
  feature — and any such feature must be advisory-only, never auto-applied to
  live risk limits without human review.
- **Never commit real config values.** `backend/config/risk_config.yaml` and
  `.env` are gitignored on purpose — only the `.example` versions belong in git.
- Run the full test suite (`pytest` in `backend/`, `npm test` in `frontend/`)
  before opening a PR.

## Reporting bugs / requesting features

Open a GitHub issue. For anything touching credential handling or the
risk engine's live-trading gate, please also read SECURITY.md first.
