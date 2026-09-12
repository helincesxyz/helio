# Runbook: one end-to-end simulated trade

Copy-paste this as a prompt to Claude Code, with Helio's service running.

---

> Using the `sma_crossover_v1` strategy, run one full simulated trade cycle
> against BTC-USDT via Helio (http://127.0.0.1:8787), following
> docs/AGENT_PROTOCOL.md:
>
> 1. Call `market_get_candles` for BTC-USDT (enough candles for a 30-period
>    SMA, e.g. 50 1-hour candles). Reshape into a MarketSnapshot.
> 2. Call `account_get_balance` and `account_get_positions` with
>    `simulatedTrading: true`. Reshape into an AccountState.
> 3. `POST /strategy/signal` with `strategy_id: "sma_crossover_v1"`, the
>    MarketSnapshot, and the AccountState. It may return zero or one intents
>    depending on whether a crossover actually occurred in this data.
> 4. If an intent was returned, `POST /risk/evaluate` with it and the same
>    account state.
> 5. If approved, call `spot_place_order` with `simulatedTrading: true`,
>    matching the intent's side/size/symbol, then `POST /learning/log/execution`
>    with the resulting order id and status.
> 6. Report what happened — including if no crossover occurred and no trade
>    was proposed, which is a normal outcome, not a failure.
>
> Stay in simulation mode throughout — do not pass `simulatedTrading: false`.

---

This exercises the full pipeline (market data → strategy → risk gate →
execution → learning log) without touching real funds.
