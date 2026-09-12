# Guard Protocol (GATE 3: PROTECT)

This extends [THESIS_PROTOCOL.md](THESIS_PROTOCOL.md) with the deterministic
safety layer between an approved (`action="BUY"`) Thesis and OKX execution.
**The guard engine contains no LLM** — it is pure, deterministic Python
(`backend/src/helio/guard/`), fully covered by unit tests.

**This protocol must never call any order-placement, order-cancellation,
order-amendment, or transfer/withdrawal MCP tool.** GATE 3 proves the risk
layer can approve or reject a proposed trade — it does not execute anything.
Helio's `GuardEngine` itself has no access to any execution tool by
construction; it only ever returns `APPROVE`/`REJECT`.

## Steps

1. Have a logged, valid, `action="BUY"` Thesis (see THESIS_PROTOCOL.md) —
   its `decision_id` is the `thesis_id` a trade intent must link to.
2. Build a `GuardTradeIntent` (see [SCHEMAS.md](SCHEMAS.md)) from that
   thesis: `entry_price`, `invalidation`, `target` copied from the thesis;
   `requested_notional`/`requested_quantity` sized within policy;
   `confidence` copied exactly from the thesis (it is cross-checked).
3. Fetch current, fresh `AccountState` via MCP (`account_get_balance` /
   `account_get_positions`, read-only) exactly as in AGENT_PROTOCOL.md.
4. `POST /guard/evaluate {"intent": {...}, "account": {...}}`.
5. If `decision.decision == "REJECT"`: **stop.** Do not call any
   order-placement MCP tool. The `rejection_reasons` list explains why.
6. If `decision.decision == "APPROVE"`: GATE 3 stops here by design — no
   execution wiring exists yet. A future gate will define the step that
   actually calls an OKX order-placement MCP tool for an approved intent,
   under its own explicit, opt-in configuration.
7. View it: `GET /guard/latest?symbol=...`, `GET /guard/for-thesis/{id}`,
   or `python3 scripts/thesis_panel.py --symbol BTC-USDT` (shows the linked
   RISK CHECK state), or `python3 scripts/risk_demo.py` for a full
   approve/reject walkthrough against synthetic data.

## Why the engine fails closed

Every rule in `guard/rules.py` returns FAIL rather than guessing when data
it needs is missing, stale, or unparseable (no account state, no thesis
found, market data older than `max_market_data_age_seconds`, ...). The
`GuardEngine` additionally wraps every rule call in a try/except — if a
rule raises an unexpected exception (an "unknown risk condition"), that is
also converted to a FAIL, never allowed to propagate into an uncaught
approval. See `docs/ARCHITECTURE.md` for the full policy list.
