# Runbook: GATE 2 live test

Copy-paste this as a prompt to Claude Code, with Helio's service running
(`make serve` from the repo root).

**This must never call any order-placement, order-cancellation,
order-amendment, or transfer/withdrawal MCP tool. Read-only reasoning only.**

---

> Run the GATE 2 live test against real BTC-USDT data, following
> docs/THESIS_PROTOCOL.md exactly:
>
> 1. Fetch live 4H, 1H, and 15m candles for BTC-USDT via `market_get_candles`
>    (at least 250 bars each — paginate if needed).
> 2. `POST /thesis/prepare` with the reshaped candle bundle.
> 3. Read the returned regime, evidence checklist, and every indicator
>    number — do not recompute anything yourself.
> 4. Write the qualitative thesis fields (thesis, prose evidence, action,
>    confidence, invalidation if BUY, target, risk_reward), copying every
>    `market_state` number verbatim from step 2's response. If action is
>    BUY, use WAIT instead unless the evidence checklist genuinely supports
>    it — do not feel compelled to produce a BUY.
> 5. `POST /thesis/submit` the assembled thesis.
> 6. Render it: `python3 scripts/thesis_panel.py --symbol BTC-USDT`.
>
> Do not call any MCP tool that places, cancels, or amends an order, or
> transfers/withdraws funds — this is a read-only reasoning exercise.
>
> Report back in exactly this format:
> ```
> GATE 2: PASS | FAIL
> REGIME: ...
> STRATEGY: ...
> ACTION: ...
> CONFIDENCE: ...
> THESIS: ...
> EVIDENCE: ...
> INVALIDATION: ...
> TARGET: ...
> WHY NOT TRADE: ...   (only if ACTION is WAIT)
> ```

---

`GATE 2: PASS` requires: live candles were fetched (not fabricated),
`/thesis/prepare` returned 200, the submitted thesis's `validation.valid`
was `true`, the cycle is visible in `GET /thesis/history`, and no
execution-tool MCP call was made at any point.
