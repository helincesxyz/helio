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
- **`backend/src/helio/thesis/`** (GATE 2: THINK) — deterministic technical
  indicators (EMA/ATR/volume/swing/price-change/volatility), a 4H regime
  classifier (BULL_TREND/BEAR_TREND/RANGE/HIGH_VOLATILITY_UNCLEAR), and the
  `trend_breakout` v1 evidence checklist. Claude Code hands over raw candles
  via `POST /thesis/prepare`; Helio computes everything and hands back a
  `PreparedMarketState`; the LLM writes the qualitative thesis and echoes
  the numbers verbatim via `POST /thesis/submit`, which `thesis/decision_quality.py`
  validates (contradiction/hallucination checks) before logging to a
  dedicated `ThesisStore`. Same credential-blind, LLM-blind pattern as the
  rest of Helio — see [THESIS_PROTOCOL.md](THESIS_PROTOCOL.md).
- **`backend/src/helio/guard/`** (GATE 3: PROTECT) — the deterministic
  safety layer between a Thesis-derived `GuardTradeIntent` and OKX
  execution. No LLM anywhere in this package. `guard/rules.py` implements
  ~20 named, documented checks (allowed symbol, spot-only, no leverage, no
  shorting, max simultaneous position, max notional, daily loss limit,
  portfolio exposure cap, invalidation/stop sanity, minimum risk/reward,
  market-data and account-state freshness, thesis linkage/validity, a WAIT
  thesis can never reach this layer, exchange lot-size/minimum-size
  precision, confidence threshold, duplicate-intent detection, and a
  cross-check that the intent's self-reported confidence actually matches
  the linked thesis). `guard/engine.py`'s `GuardEngine.evaluate()` runs
  every rule regardless of earlier failures (so a rejection always lists
  every applicable violation, not just the first) and wraps each rule call
  so an unexpected exception becomes a FAIL rather than an uncaught
  approval. Every evaluation — approved or rejected — is logged to a
  dedicated `GuardStore`. See [GUARD_PROTOCOL.md](GUARD_PROTOCOL.md).
- **[AGENT_PROTOCOL.md](AGENT_PROTOCOL.md)** / **[THESIS_PROTOCOL.md](THESIS_PROTOCOL.md)**
  / **[GUARD_PROTOCOL.md](GUARD_PROTOCOL.md)** — the actual contracts for
  how Claude Code sequences MCP calls and Helio API calls. As load-bearing
  as any code file here.

## Limitations

- No headless/unattended trading loop in v1 — a human-initiated Claude Code
  session drives every cycle.
- Risk rules use simplified notional/exposure estimates (documented in
  `risk/rules.py`); they fail closed (reject) when they can't compute a
  needed value rather than guessing.
- The learning engine only logs and retrieves history in v1; it does not
  yet adapt strategy parameters (see `learning/adjuster.py`).
- Single-strategy, single-exchange (OKX) scope for this initial pass.
- GATE 2's `trend_breakout` strategy only produces a reasoning thesis
  (BUY/WAIT + evidence) — it does not place orders. That wiring is
  deliberately out of scope until a later gate, and execution-tool access
  is intentionally not given to the agent for this pass.
- GATE 3's `GuardEngine` can only APPROVE or REJECT a trade intent — an
  APPROVE does not (yet) cause anything to execute. Wiring an approved
  intent to an actual OKX order-placement MCP call is explicitly deferred
  to a later gate, under its own opt-in configuration.
- GATE 3's risk policy is a single, conservative starting point (BTC-USDT
  spot, long-only, one position, small notional/exposure caps). It is not
  tuned or backtested — the numeric thresholds are documented, sane
  defaults meant to be adjusted via `backend/config/guard_config.yaml`.
- The frontend's consumer-facing Low/Balanced/High risk selector
  (`frontend/src/components/risk/RiskSelector.tsx`) reads three real,
  independent `GuardConfig` profiles via `GET /guard/profiles`
  (`backend/config/guard_profile_{low,balanced,high}.yaml`) — not a
  client-side scaling preview. `AppState.guard_profiles` loads all three
  once at startup, immutably; `AppState.get_guard_engine(profile)`
  constructs a fresh, stateless `GuardEngine` per request (no shared
  mutable state). `build_app_state()` asserts a hard invariant at startup:
  the three profiles must agree on every safety-critical field (allowed
  symbol/instrument/leverage/side, exchange lot/min size) — only the
  bounded numeric knobs (notional/daily-loss/exposure/confidence/
  risk-reward caps) may vary between tiers. `GuardTradeIntent.risk_profile`
  selects which profile `/guard/evaluate` actually applies; an unrecognized
  value is rejected (422) rather than silently falling back.
