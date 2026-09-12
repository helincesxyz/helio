# Helio

Helio is an open-source, LLM-assisted crypto trading assistant for OKX. An
LLM (via [Claude Code](https://claude.com/claude-code)) proposes trades; a
deterministic, auditable risk engine approves or rejects them; only approved
trades are ever executed, exclusively through the official
[OKX Agent Trade Kit](https://okx.com) MCP server. Helio's own code never
sees, stores, or transmits an OKX API key, secret, or passphrase.

## What Helio does

- Defines a structured `TradeIntent` contract an LLM or strategy can propose.
- Runs every intent through a pure, deterministic `RiskEngine` (position
  limits, notional caps, leverage caps, daily loss limits, exposure caps, and
  a hard simulation-vs-live gate) before it can be executed.
- Ships one example strategy (SMA crossover) behind a pluggable `Strategy`
  interface.
- Logs every intent, decision, execution, and outcome to a local SQLite
  event store — the working half of a "recursive learning" engine (the
  adaptive half is an honest, documented stub in this version).
- Serves a small React dashboard showing connection status, account state,
  active risk limits, and recent trade activity.
- Never runs its own OKX network client — see [Architecture](#architecture).

## Architecture

Helio's backend cannot call OKX MCP tools directly — only the Claude Code
agent process can. Rather than build a second, parallel OKX client, Helio is
entirely credential-blind: **all** OKX I/O (market data, account state, order
placement) flows through Claude Code calling
`mcp__okx-agent-trade-kit__*` tools. Helio is a local library + a
`127.0.0.1`-only FastAPI service that Claude Code calls with plain,
non-secret JSON.

```
Claude Code  --MCP-->  OKX Agent Trade Kit  --signed request-->  OKX
     |
     |--HTTP (127.0.0.1:8787)--> Helio (risk engine, strategy engine, learning log)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full data flow and
the reasoning behind this design, and [docs/AGENT_PROTOCOL.md](docs/AGENT_PROTOCOL.md)
for the exact step-by-step contract Claude Code follows.

### OKX Trade Kit integration

Helio depends on the OKX Agent Trade Kit being installed and authenticated
as an MCP server available to Claude Code. See
[docs/OKX_SETUP.md](docs/OKX_SETUP.md) — Helio never touches the Trade Kit's
credential store directly; it only checks that `system_get_capabilities`
reports `hasAuth: true`.

### MCP integration

Every MCP tool call in this system is made by Claude Code, never by Helio's
Python process. Helio only receives already-fetched, reshaped, non-secret
JSON over its local API. See [docs/AGENT_PROTOCOL.md](docs/AGENT_PROTOCOL.md).

### Strategy engine

`backend/src/helio/strategy/` — a `Strategy` ABC
(`generate_intents(market, account, params) -> list[TradeIntent]`) plus one
example, `sma_crossover_v1`. Add new strategies by implementing the
interface and registering them in `strategy/registry.py`.

### Risk engine

`backend/src/helio/risk/` — pure functions, one per rule, aggregated by
`RiskEngine.evaluate()`. Configured by `backend/config/risk_config.yaml`
(copy from the `.example` file). The most important rule is
`sim_vs_live_gate`: a `mode="live"` intent is rejected unless
`allow_live: true` is explicitly set.

### Recursive learning

`backend/src/helio/learning/` — `EventStore` (SQLite) logs every intent,
decision, execution, and outcome and supports history queries today. Its
`ParameterAdjuster` is an explicit, documented stub in this version: it
always returns `None`. A future version could compute advisory
parameter-tuning suggestions from history, but any such feature must remain
advisory-only, reviewed by a human before it ever changes a risk limit.

## Install

```bash
git clone <this-repo>
cd helio

# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cd ..

# Frontend
cd frontend
npm install
cd ..
```

## Configure OKX locally

Helio does not configure OKX itself. Install and authenticate the OKX Agent
Trade Kit per its own official documentation, then confirm it's registered
as an MCP server for Claude Code. Full details: [docs/OKX_SETUP.md](docs/OKX_SETUP.md).

Then set up Helio's own (non-secret) config. **Run Helio's CLI/service from
the repo root** (not from `backend/`) — its config and build paths are
repo-root-relative:

```bash
source backend/.venv/bin/activate
python -m helio.cli.main init-config   # creates backend/config/risk_config.yaml + strategy_config.yaml
# edit backend/config/risk_config.yaml — review limits before running anything
cp .env.example .env                   # optional; defaults already match .env.example
```

## Run tests

```bash
cd backend && pytest
cd ../frontend && npm test && npm run build
```

## Run in read-only / simulation mode (default)

```bash
source backend/.venv/bin/activate && python -m helio.cli.main serve   # http://127.0.0.1:8787, run from repo root
cd frontend && npm run dev                                            # http://localhost:5173
```

Or both together: `./scripts/dev_up.sh` (from the repo root).

`HELIO_MODE=simulation` is the default. With `risk_config.yaml`'s
`allow_live: false` (also the default), no live order can ever be approved.
Ask Claude Code to run [docs/runbooks/verify.md](docs/runbooks/verify.md) or
[docs/runbooks/simulate_trade.md](docs/runbooks/simulate_trade.md) to
exercise the full pipeline against OKX's simulated-trading environment.

## Run the verification checklist

```bash
source backend/.venv/bin/activate && python -m helio.cli.main verify   # local checks only, run from repo root
```

For the full 8-row checklist (including the OKX/MCP-sourced rows), see
[docs/VERIFICATION_PROTOCOL.md](docs/VERIFICATION_PROTOCOL.md) and run
[docs/runbooks/verify.md](docs/runbooks/verify.md) with Claude Code, then
check `curl http://127.0.0.1:8787/verify` or the dashboard.

## Enable live trading

This is a deliberate, two-step opt-in — do not do this without reviewing
your risk limits first:

1. Set `allow_live: true` in `backend/config/risk_config.yaml`.
2. Set `HELIO_MODE=live` in `.env` (or your environment).
3. Have Claude Code pass `simulatedTrading: false` and `intent.mode: "live"`
   consistently for any intent you actually want executed for real.

Even in live mode, every other risk rule (notional caps, position limits,
leverage caps, daily loss limit, exposure cap, allowed instruments) still
applies exactly as in simulation.

## Security considerations

- Helio's code never reads, stores, logs, or accepts OKX credentials — see
  [SECURITY.md](SECURITY.md) for the full policy and the defense-in-depth
  measures (schema `extra="forbid"`, log redaction, localhost-only binding).
- Review `backend/config/risk_config.yaml` before ever setting `allow_live: true`.
- The FastAPI service is not authenticated — it's designed to be
  `127.0.0.1`-only and never exposed beyond your machine.

## Limitations

- No unattended/headless trading loop in this version — a Claude Code
  session must be actively driving each cycle.
- Risk rules use simplified notional/exposure estimates and fail closed
  (reject) when they can't compute a needed value — see `risk/rules.py`.
- The learning engine logs history but does not yet adapt strategy
  parameters (`learning/adjuster.py` is an explicit stub).
- One example strategy, one exchange (OKX), spot instruments only by
  default — extend via the `Strategy` interface and `risk_config.yaml`.

## License

[MIT](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
