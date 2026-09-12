# Runbook: run the full verification checklist

Copy-paste this as a prompt to Claude Code, with Helio's service already
running (`make serve` or `helio serve`) and the frontend built
(`cd frontend && npm run build`).

---

> Run the Helio verification checklist end to end, in simulation mode only.
> Helio's API is at http://127.0.0.1:8787. Follow docs/AGENT_PROTOCOL.md:
>
> 1. Call `system_get_capabilities`. POST the result to `/verify/report` as
>    the `"OKX CONNECTION"` check (PASS if `hasAuth` is true).
> 2. Call `account_get_balance` and `account_get_positions` with
>    `simulatedTrading: true`. POST `/verify/report` for `"ACCOUNT"` and
>    `"PORTFOLIO"`.
> 3. Call `market_get_ticker` for `BTC-USDT`. POST `/verify/report` for
>    `"MARKET DATA"`.
> 4. Build a small TradeIntent (`mode: "simulation"`, a tiny size, an
>    instrument in the active risk config's `allowed_instruments`) and
>    `POST /risk/evaluate`. If rejected, stop and report why — do not force it.
> 5. If approved, call `spot_place_order` with `simulatedTrading: true` and a
>    tiny size, then `spot_get_orders` / `spot_cancel_order` to close it out.
>    POST `/verify/report` for `"SPOT EXECUTION"`.
> 6. `GET /verify` and paste back the full table.
>
> Do not use `simulatedTrading: false` at any point in this runbook, and
> never paste any OKX credential, token, or config file contents anywhere
> in this conversation.

---

Expect all 8 rows to show `PASS`. If any MCP-sourced row is missing, it
means that step wasn't run yet — `NOT RUN` and `STALE` are informative, not
errors, until you've actually completed the corresponding step.
