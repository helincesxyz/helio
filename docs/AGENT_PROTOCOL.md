# Agent Protocol

This is the contract Claude Code follows when acting as Helio's orchestrator.
Helio's FastAPI service (default `http://127.0.0.1:8787`) never talks to OKX
itself — every step that touches OKX is an explicit MCP tool call made by
Claude Code, not by Helio.

**Rule zero: never paste OKX credential file contents, tokens, API keys, or
secrets into any prompt, log line, or Helio API payload.** Helio has no field
for them and will reject unknown fields (`extra="forbid"`), but don't rely on
that — just never produce them in the first place.

## 1. Connectivity check

Call `mcp__okx-agent-trade-kit__system_get_capabilities`. Report the result:

```
POST /verify/report
{"check": "OKX CONNECTION", "status": "PASS" | "FAIL", "detail": "hasAuth=<bool> demo=<bool>"}
```

PASS requires `hasAuth: true` in the response.

## 2. Account state

Call `account_get_balance` and `account_get_positions` (with `simulatedTrading`
matching the current `HELIO_MODE`). Reshape into an `AccountState` (see
[SCHEMAS.md](SCHEMAS.md)) and either:

```
POST /state/account   {..AccountState..}
```

and/or include it directly in a `/risk/evaluate` call. Report:

```
POST /verify/report {"check": "ACCOUNT", "status": "PASS", "detail": "..."}
POST /verify/report {"check": "PORTFOLIO", "status": "PASS", "detail": "<n> open positions"}
```

## 3. Market data

Call `market_get_ticker` and/or `market_get_candles`. Reshape into a
`MarketSnapshot` and optionally `POST /state/market` or feed it straight into
`POST /strategy/signal`. Report:

```
POST /verify/report {"check": "MARKET DATA", "status": "PASS", "detail": "<instId> last=<price>"}
```

## 4. Form a TradeIntent

Either take the list returned by `POST /strategy/signal`, or construct one
directly from your own reasoning. Always set `mode` to the current
`HELIO_MODE` — never hardcode `"live"`.

## 5. Risk check — mandatory gate

```
POST /risk/evaluate {"intent": {...}, "account": {...}}
```

If `approved` is `false`: **stop.** Do not call any order-placement MCP tool
for this intent. The rejection reasons are in the response.

## 6. Execute (only if approved)

Call the matching order tool for `intent.instrument_type`
(`spot_place_order`, `swap_place_order`, `futures_place_order`, …) with
`simulatedTrading` set from `intent.mode` (`simulation` → `true`,
`live` → `false`). For the SPOT EXECUTION verification check specifically,
use a tiny size, `simulatedTrading: true`, then cancel the order and confirm
via `spot_get_orders` / `spot_cancel_order`. Report:

```
POST /verify/report {"check": "SPOT EXECUTION", "status": "PASS", "detail": "placed+cancelled ordId=..."}
```

## 7. Log the outcome

```
POST /learning/log/execution {"intent_id": "...", "result": {"ord_id": "...", "status": "..."}}
# later, once the position is closed or PnL is known:
POST /learning/log/outcome {"intent_id": "...", "outcome": {"realized_pnl_usd": "..."}}
```

## Running the full checklist

See [runbooks/verify.md](runbooks/verify.md) for a copy-pasteable prompt that
walks through steps 1–6 in simulation mode and leaves `GET /verify` showing
PASS across all 8 categories.
