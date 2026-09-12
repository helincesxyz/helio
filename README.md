# Helio

Helio is an open-source, LLM-assisted investing agent for OKX. You tell it
what you want your money to do in plain English; it fetches real OKX market
and account data, reasons about it with a deterministic technical-analysis
engine, checks any proposed trade against a deterministic risk engine, and —
only once approved — prepares a real, exactly-specified order for OKX. Helio
never holds, reads, or transmits your OKX API key, secret, or passphrase,
and it never submits a real (live) order on its own — a human always makes
that final call.

## The gated pipeline

Helio is built as five gates, each one real and independently testable:

1. **SEE** — read-only OKX connection: account balance, positions, market
   data, via the official OKX Agent Trade Kit MCP server.
2. **THINK** (`backend/src/helio/thesis/`) — deterministic technical
   analysis (EMA20/50/200, ATR, volume, swing high/low) across 4H/1H/15m,
   producing a regime classification and a BUY/WAIT thesis with an
   evidence checklist. No LLM invents a number here — the LLM writes the
   qualitative reasoning and must echo the computed numbers verbatim,
   cross-checked for hallucination.
3. **PROTECT** (`backend/src/helio/guard/`) — a pure, deterministic risk
   engine with ~20 named rules (allowed symbol, spot-only, no leverage, no
   shorting, position/notional/exposure caps, daily loss limit,
   invalidation/risk-reward sanity, data freshness, duplicate detection,
   exchange lot-size precision, confidence threshold). Fails closed:
   anything it can't verify is rejected, never assumed safe. Runs under
   one of three real, independent, backend-enforced risk profiles
   (low/balanced/high) — see [docs/GUARD_PROTOCOL.md](docs/GUARD_PROTOCOL.md).
4. **ACT** (`backend/src/helio/execution/`) — the execution gateway between
   an approved trade and an actual OKX order: exact-intent-bound,
   single-use, short-lived authorizations; a kill switch
   (`HELIO_LIVE_EXECUTION_ENABLED`, environment-variable only) gating any
   live submission; and — even with the switch on — Helio/Claude Code
   never calls the live order-placement tool itself. It hands back the
   exact order parameters, and the account owner submits that call
   themselves. Fully real and tested in OKX's simulated-trading mode. See
   [docs/EXECUTION_PROTOCOL.md](docs/EXECUTION_PROTOCOL.md).
5. **LEARN** (`backend/src/helio/learning/`) — an event log exists and
   works; adaptive parameter tuning from history is an explicit,
   documented stub in this version (`learning/adjuster.py` always returns
   `None`).

## The conversation bridge

Helio's backend has no OKX or LLM access of its own — only Claude Code can
call the OKX MCP tools, and only within an active session. So the frontend
doesn't talk to OKX directly: it posts your message as a pending request
(`backend/src/helio/conversation/`), and a live Claude Code session fetches
genuinely fresh OKX data, runs it through the real pipeline above, and posts
the structured answer back. See
[docs/runbooks/conversation_fulfillment.md](docs/runbooks/conversation_fulfillment.md).
This means Helio isn't an unattended trading bot — every cycle needs a human
actively driving a Claude Code session, by design.

## The frontend

A React app (`frontend/`) built around natural-language intent rather than
strategy configuration:

- **Home** — real account balance, a single input for what you want your
  money to do, and a Low/Balanced/High risk selector showing the real
  numbers each tier actually enforces (not a client-side preview).
- **Agent** — a conversational view; every answer traces to a real
  analysis or an honest "not available yet," with progressive disclosure
  from plain English into the full technical evidence trail and raw JSON.
- **Strategy** (Overview/Performance/Decisions/Trades/Memory) — a real BTC
  price chart with EMA overlays, full decision history, a
  numbered "How Helio decided" trace spanning all five gates, and Gate 4
  execution records labeled honestly as "Execution test" vs "Autonomous
  strategy" (the latter doesn't exist yet — see Limitations).

## Architecture

```
You (UI)  --HTTP-->  Helio (127.0.0.1:8787, FastAPI + SQLite)
                            ^
                            | HTTP (posts fetched data, posts answers back)
                            v
Claude Code  --MCP-->  OKX Agent Trade Kit  --signed request-->  OKX
```

No arrow ever carries an OKX credential — Helio only ever sees JSON that
Claude Code already received back from an MCP tool call. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full data flow and the
reasoning behind this design, and [docs/AGENT_PROTOCOL.md](docs/AGENT_PROTOCOL.md) /
[docs/THESIS_PROTOCOL.md](docs/THESIS_PROTOCOL.md) /
[docs/GUARD_PROTOCOL.md](docs/GUARD_PROTOCOL.md) /
[docs/EXECUTION_PROTOCOL.md](docs/EXECUTION_PROTOCOL.md) for the exact
step-by-step contracts Claude Code follows at each gate.

### OKX Trade Kit integration

Helio depends on the OKX Agent Trade Kit being installed and authenticated
as an MCP server available to Claude Code. See
[docs/OKX_SETUP.md](docs/OKX_SETUP.md) — Helio never touches the Trade Kit's
credential store directly.

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
python -m helio.cli.main init-config
# creates backend/config/{risk,strategy,guard}_config.yaml and
# guard_profile_{low,balanced,high}.yaml — review the guard profiles
# especially; they're what Gate 3 actually enforces per risk tier.
cp .env.example .env   # optional; defaults already match .env.example
```

## Run tests

```bash
cd backend && pytest
cd ../frontend && npx tsc -b && npm test && npm run build
```

## Run it

```bash
source backend/.venv/bin/activate && python -m helio.cli.main serve   # http://127.0.0.1:8787, run from repo root
cd frontend && npm run dev                                            # http://localhost:5173
```

Or both together: `./scripts/dev_up.sh` (from the repo root).

With a Claude Code session active and watching for pending requests (see
[docs/runbooks/conversation_fulfillment.md](docs/runbooks/conversation_fulfillment.md)),
open the frontend and type a request like "Get into BTC." Without an active
session fulfilling requests, the UI will sit in a "reasoning..." state
indefinitely — that's the one real limitation of this architecture, not a
bug.

## Run the verification checklist

```bash
source backend/.venv/bin/activate && python -m helio.cli.main verify   # local checks only, run from repo root
```

For the full checklist (including the OKX/MCP-sourced rows), see
[docs/VERIFICATION_PROTOCOL.md](docs/VERIFICATION_PROTOCOL.md) and run
[docs/runbooks/verify.md](docs/runbooks/verify.md) with Claude Code, then
check `curl http://127.0.0.1:8787/verify`, the dashboard, or:

```bash
python3 scripts/health_check.py   # standard-library only; needs `serve` running
```

`python3 scripts/risk_demo.py` renders a real APPROVE and a real REJECT
against the Gate 3 risk engine as an ASCII panel.

## Live execution — how it actually works

There is no config flag that makes Helio place a real order by itself. The
path is deliberately narrow:

1. A trade intent gets a real `APPROVE` from Gate 3.
2. `POST /execution/authorize` — a single-use, 5-minute authorization tied
   to that exact intent.
3. `POST /execution/prepare` with `mode: "live"` — blocked with `403`
   unless `HELIO_LIVE_EXECUTION_ENABLED` is set in the **environment**
   (never in a request body, never settable through the UI or by an LLM).
   If unblocked, it returns the exact OKX order parameters.
4. **A human — not Claude Code, not Helio — submits that exact call to
   OKX themselves.** Only they can move real money.
5. The resulting order and account state get verified and recorded via
   `POST /execution/verify`, producing the full `ExecutionLifecycle` shown
   on the Trades page.

Every step through 3 is real and fully tested, including a real submission
to OKX's own simulated-trading endpoint. Step 4 is a hard line, independent
of the kill switch: it isn't a permission Helio can grant. See
[docs/EXECUTION_PROTOCOL.md](docs/EXECUTION_PROTOCOL.md).

## Security considerations

- Helio's code never reads, stores, logs, or accepts OKX credentials — see
  [SECURITY.md](SECURITY.md) for the full policy and the defense-in-depth
  measures (schema `extra="forbid"`, log redaction, localhost-only binding).
- Review `backend/config/guard_profile_*.yaml` before relying on any risk
  tier — `build_app_state()` asserts they can't weaken safety-critical
  fields relative to each other, but the numeric caps are still yours to
  set deliberately.
- The FastAPI service is not authenticated — it's designed to be
  `127.0.0.1`-only and never exposed beyond your machine.

## Limitations

- No unattended/headless trading loop — a Claude Code session must be
  actively driving each cycle; there is no standalone service with its own
  OKX or LLM credentials.
- Every trade shown in this version is a manually-initiated "execution
  test," never an autonomous strategy — Gate 5 (learning) doesn't adapt
  strategy parameters yet, so there's no closed loop that could trade on
  its own even if the credential/architecture constraint above were lifted.
- Risk rules use simplified notional/exposure estimates and fail closed
  (reject) when they can't compute a needed value — see `guard/rules.py`.
- One example strategy (`trend_breakout v1`), one exchange (OKX), spot
  BTC-USDT only by default — extend via the `strategy`/`guard` config.
- OKX Earn/APY optimization is discovery-only — no subscribe/redeem call
  exists anywhere in this codebase.

## License

[MIT](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
