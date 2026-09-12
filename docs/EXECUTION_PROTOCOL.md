# Execution Protocol (GATE 4: ACT)

This extends [GUARD_PROTOCOL.md](GUARD_PROTOCOL.md) with the one path from
an already-`APPROVE`d `GuardDecision` to an actual OKX order. Everything in
`backend/src/helio/execution/` is real, working code, exercised end to end
in **simulation** by the backend test suite. The **live** path is the exact
same code — the only difference is who submits the final order.

**This protocol calls `spot_place_order` / `spot_cancel_order` (and their
`spot_get_order` / `account_get_balance` read-only counterparts) with
`simulatedTrading: true` for every simulation test in this codebase. A
`simulatedTrading: false` call is never made by Claude Code autonomously —
the human account owner submits that exact call themselves, using the
exact parameters `/execution/prepare` returns.** This is an absolute rule,
not a configuration option: no request body field, prompt, or environment
setting available to an LLM changes it.

## The kill switch

`HELIO_LIVE_EXECUTION_ENABLED` (env var, default unset/off) is checked,
unconditionally, the moment `/execution/prepare` is called with
`mode="live"`. It is never a request body field — no LLM output and no API
payload can flip it. `backend/src/helio/execution/kill_switch.py` reads it
fresh on every check.

## Steps

1. Have a logged `GuardDecision` with `decision == "APPROVE"` (see
   GUARD_PROTOCOL.md) — its `trade_intent_id` is what gets authorized.
2. `POST /execution/authorize {"trade_intent_id": ..., "origin": "execution_test"}`.
   Fails (409) if the decision was a REJECT, or if this `trade_intent_id`
   already has an authorization (the `ExecutionStore`'s `trade_intent_id`
   UNIQUE constraint enforces this at the database level — one approved
   intent gets at most one authorization, ever, whether or not it's used).
   Returns an `ExecutionAuthorization`: `execution_id`, an `intent_hash`
   (sha256 of the exact approved intent, for audit), and a 5-minute
   `expires_at`.
3. `POST /execution/prepare {"execution_id": ..., "mode": "simulation" | "live"}`.
   For `mode="live"`, this is where the kill switch is checked (403 if
   off). Returns the exact MCP call parameters (`instId`, `side`,
   `ordType`, `sz`, `simulatedTrading`) — this is the record Claude Code
   reads to know exactly what to call for simulation, and the record the
   user reads to know exactly what to submit themselves for live.
4. **Simulation only**: Claude Code calls `spot_place_order` via MCP with
   those exact parameters and `simulatedTrading: true`.
   **Live**: Claude Code hands the user this exact preparation record and
   stops — the user calls `spot_place_order` themselves (outside Claude
   Code, or by explicitly instructing their own OKX client) with
   `simulatedTrading: false`, then reports the raw response back.
5. `POST /execution/record-submission` with the parsed OKX response
   (`okx_order_id`, `okx_code`, `okx_scode`). Marks the authorization
   consumed — one-shot, no reuse, no blind retry on failure. Sets status
   `SUBMITTED` (simulation, accepted) or `LIVE` (live, accepted) or
   `REJECTED` (OKX rejected the order).
6. Fetch the real order state (`spot_get_order`) and real post-trade
   account state (`account_get_balance`) via MCP, and
   `POST /execution/verify` with both (plus the pre-trade account state
   from step 1's context, if available). Finalizes `FILLED` /
   `PARTIALLY_FILLED` / `UNKNOWN`. **`UNKNOWN` is terminal** — nothing in
   `execution/gateway.py` re-authorizes or retries from an `UNKNOWN`
   verification; a human has to look at it.
7. `GET /execution/{execution_id}` or `GET /execution?thesis_id=...` to
   view the full `ExecutionLifecycle` (every ID, every stage timestamp,
   pre/post account state) — this is what the Trades page and any final
   report read from.

## Idempotency, by construction

- One `trade_intent_id` → at most one `ExecutionAuthorization`, enforced by
  a DB UNIQUE constraint, not just application logic.
- One authorization → at most one submission (`consumed` flips permanently
  on the first `record-submission` call, success or rejection).
- One submission → at most one verification (`verified_at` is set once;
  a second `/execution/verify` call for the same `execution_id` is
  rejected, 409).
- `UNKNOWN` is a terminal status. There is no retry loop anywhere in this
  package.

## Origin

Every execution created through this manual, human-initiated flow is
`origin: "execution_test"` — including the one real live BTC-USDT test
buy this milestone produces. `origin: "autonomous_strategy"` is reserved
for a future unattended trading loop (Gate 5+) that does not exist yet;
nothing in this codebase ever sets it. The Trades page must show this
distinction honestly, never implying autonomous trading has happened.
