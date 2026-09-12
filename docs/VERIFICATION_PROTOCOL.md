# Verification Protocol

Helio's status checklist has 8 rows. They don't all run the same way —
some are pure local checks, some can only be produced by Claude Code calling
OKX Agent Trade Kit MCP tools.

| Check | Runs via | How |
|---|---|---|
| RISK ENGINE | Local (`helio verify` or `GET /verify`) | Runs canned intents through `RiskEngine` in-process; confirms `sim_vs_live_gate` rejects a live intent by default |
| LEARNING ENGINE | Local | Round-trip write/read against the SQLite event store (`EventStore.self_test()`) |
| UI | Local | Checks `frontend/dist/index.html` exists (i.e. `npm run build` has been run); full check also includes `npm test` |
| OKX CONNECTION | Claude Code + MCP | `system_get_capabilities`, checks `hasAuth: true` |
| ACCOUNT | Claude Code + MCP | `account_get_balance` (matching `simulatedTrading`) |
| MARKET DATA | Claude Code + MCP | `market_get_ticker` |
| PORTFOLIO | Claude Code + MCP | `account_get_positions` |
| SPOT EXECUTION | Claude Code + MCP | `spot_place_order` (tiny size, `simulatedTrading: true`) then `spot_cancel_order` |

## How the merge works

- `helio verify` (CLI) only ever prints the three local rows — it cannot make
  MCP calls itself.
- The FastAPI service exposes `GET /verify`, which merges the three local
  rows (computed live on every request) with the five MCP-sourced rows.
  MCP-sourced rows come from whatever was last POSTed to `POST /verify/report`
  and are marked `STALE` if older than 15 minutes, or `NOT RUN` if nothing has
  been reported yet.
- The dashboard's Verification Checklist renders `GET /verify` directly.

## Running it end to end

1. `cd backend && helio verify` — confirms RISK ENGINE and LEARNING ENGINE
   pass; run `cd frontend && npm run build` first so UI passes too.
2. `helio serve` (or `make serve`) to start the local API.
3. Ask Claude Code to follow [runbooks/verify.md](runbooks/verify.md), which
   walks through the 5 MCP-sourced checks in **simulation mode only** and
   POSTs each result to `/verify/report`.
4. `curl http://127.0.0.1:8787/verify` (or load the dashboard) and confirm
   all 8 rows show PASS.

A `mode="live"` intent should still be rejected by `RiskEngine` by default —
that's checked automatically as part of the RISK ENGINE row, not something
you need to verify by hand.
