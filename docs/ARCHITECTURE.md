# Helio Architecture

## The problem this solves

We want an LLM to be able to reason about trades on OKX, but we never want
the LLM (or any Helio code) to hold, see, or transmit OKX API credentials,
and we never want an LLM's trade idea to reach OKX without passing a
deterministic, auditable check first.

## The two systems Helio sits between

1. **The OKX Agent Trade Kit**, exposed here as an MCP server
   (`mcp__okx-agent-trade-kit__*` tools). It owns OKX authentication
   entirely — it signs requests locally using its own credential store and
   never hands the raw key/secret/passphrase to the calling agent. Only the
   Claude Code agent process can invoke these MCP tools.
2. **Claude Code**, the LLM agent that reads market/account data via those
   MCP tools and decides what to propose.

## Why Helio has no OKX client of its own

Helio's Python backend cannot call MCP tools directly — only Claude Code can.
Two designs were possible:

- Give Helio its own OKX REST client (at least for reads) and gate only
  writes through MCP. **Rejected**: this creates a second, parallel path to
  OKX, likely needing its own key, and defeats the goal of a single,
  auditable credential boundary.
- Make Helio credential-blind end to end: it never talks to OKX, in any
  form. **Chosen.** `grep -r "okx\|api_key\|secret" backend/src/helio` should
  turn up nothing — that's the whole point.

The tradeoff: Helio cannot run as an unattended daemon. It only acts while
Claude Code is actively driving a session and choosing to call MCP tools per
the protocol below. That's intentional — the point of this system is an
LLM-in-the-loop trade with a deterministic gate, not a cron-job bot.

## Data flow

```
Claude Code                          Helio (127.0.0.1:8787, FastAPI)         OKX
    |                                          |                              |
    |--- market_get_ticker/candles (MCP) ------------------------------------>|
    |<--------------------------------------------------------- price/candles-|
    |--- POST /state/market or /strategy/signal --> reshape into intents      |
    |                                          |                              |
    |--- POST /risk/evaluate {intent,account} ->  RiskEngine.evaluate()       |
    |<----------------------------------------- RiskDecision                 |
    |                                          |                              |
    | if approved:                             |                              |
    |--- spot_place_order (MCP, simulatedTrading from intent.mode) --------->|
    |<---------------------------------------------------------- order result|
    |--- POST /learning/log/execution -------->  EventStore                  |
    |--- POST /learning/log/outcome (later) -->  EventStore                  |
```

No arrow in this diagram ever carries a credential. Helio only ever sees
JSON that Claude Code already received back from an MCP tool call.

## Components

- **`backend/src/helio/schemas/`** — the JSON contract for every payload
  (see [SCHEMAS.md](SCHEMAS.md)).
- **`backend/src/helio/risk/`** — pure, deterministic risk rules + engine.
  The security-critical component; zero I/O.
- **`backend/src/helio/strategy/`** — pluggable signal generators (one
  example: SMA crossover). No ML in v1.
- **`backend/src/helio/learning/`** — SQLite event log (real) + an advisory
  parameter-adjustment interface (explicit stub in v1 — see the docstring in
  `learning/adjuster.py`).
- **`backend/src/helio/service/`** — the FastAPI app Claude Code and the
  dashboard talk to. Binds `127.0.0.1` only.
- **`frontend/`** — a React dashboard reading only from Helio's own API.
- **[AGENT_PROTOCOL.md](AGENT_PROTOCOL.md)** — the actual contract for how
  Claude Code sequences MCP calls and Helio API calls. As load-bearing as
  any code file here.

## Limitations

- No headless/unattended trading loop in v1 — a human-initiated Claude Code
  session drives every cycle.
- Risk rules use simplified notional/exposure estimates (documented in
  `risk/rules.py`); they fail closed (reject) when they can't compute a
  needed value rather than guessing.
- The learning engine only logs and retrieves history in v1; it does not
  yet adapt strategy parameters (see `learning/adjuster.py`).
- Single-strategy, single-exchange (OKX) scope for this initial pass.
