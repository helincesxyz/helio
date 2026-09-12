# Thesis Protocol (GATE 2: THINK)

This is the contract Claude Code follows to turn live OKX candles into a
structured, machine-readable trading thesis. It extends the same pattern as
[AGENT_PROTOCOL.md](AGENT_PROTOCOL.md): Helio's backend never calls OKX and
never calls an LLM — Claude Code fetches data via MCP, Helio computes
deterministic indicators/regime/evidence and hands them back, Claude Code
(the LLM) writes the qualitative thesis and echoes the numbers verbatim, and
Helio validates and logs the result.

**This protocol must never call any order-placement, order-cancellation,
order-amendment, or transfer/withdrawal MCP tool** (`spot_place_order`,
`spot_cancel_order`, `spot_amend_order`, `swap_place_order`,
`futures_place_order`, `option_place_order`, `dca_create_order`,
`grid_create_order`, `account_transfer`, `earn_*`, `onchain_earn_*`, etc.).
GATE 2 is read-only reasoning only — no execution tools are used or needed.

## Steps

1. **Fetch candles.** Call `market_get_candles` for the symbol at `bar=4H`,
   `bar=1H`, and `bar=15m` — at least `MIN_CANDLES_REQUIRED` (250) bars for
   each timeframe. Paginate with `after`/`before` if a single call caps
   below that.
2. **Reshape into a CandleBundle**: `{"symbol": "...", "tf_4h": [...],
   "tf_1h": [...], "tf_15m": [...]}`, each candle as
   `{"ts", "o", "h", "l", "c", "vol"}` (matching `schemas.market.Candle`).
3. **`POST /thesis/prepare`** with the bundle. Helio computes EMA20/50/200,
   ATR, volume ratio, swing high/low, price change, volatility, the regime,
   and the 7-item evidence checklist — all deterministically, in Python.
   A 422 response means insufficient/invalid data (see the error detail).
4. **Read the returned `PreparedMarketState`.** Every number, the regime,
   the regime reason, and the evidence checklist (with a `candidate_action`
   reference — never surface this as the final action) are in this response.
5. **As the LLM, write the qualitative fields**: `thesis` (prose),
   `evidence` (prose bullets — separate from the checklist you just read),
   `action` (`BUY`/`WAIT` — **WAIT is a first-class, always-valid answer**),
   `confidence` (0–1), `invalidation` (required if `action="BUY"`), `target`,
   `risk_reward`. **Copy every number in `market_state` verbatim** from step
   4's response — do not recompute, round differently, or invent anything.
   If evidence conflicts (e.g. `timeframes_consistent` failed), say so
   explicitly in the `thesis` text.
6. **`POST /thesis/submit`** the assembled `Thesis`. A 422 means the payload
   itself was malformed (missing/wrong-typed field, confidence out of
   [0,1], or no prepared state cached for this symbol — call step 3 first).
   A 200 with `validation.valid: false` means the payload was well-formed
   but failed a semantic check (contradicts the regime, unsupported by the
   evidence, missing invalidation on a BUY, or a numeric value doesn't match
   what Helio computed — treat that as a possible hallucination, not a
   signal). Either way, the cycle is always logged.
7. **View it**: `GET /thesis/latest?symbol=...`, `GET /thesis/history`, or
   `python3 scripts/thesis_panel.py --symbol BTC-USDT` for the terminal panel.

If `validation.valid` is `false`, do not treat the thesis as a trading
signal — report the errors, and if warranted, revise `action` to `WAIT` and
resubmit rather than forcing a BUY through.
