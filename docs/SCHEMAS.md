# Helio Data Schemas

Canonical definitions live in `backend/src/helio/schemas/*.py` (Pydantic models,
all with `extra = "forbid"`). This document mirrors them for quick reference.
None of these types ever carries an OKX credential.

## TradeIntent

A structured, non-executing proposal to trade. Produced by an LLM or a
`Strategy`; must pass `RiskEngine.evaluate()` before any OKX order tool is called.

| Field | Type | Notes |
|---|---|---|
| `intent_id` | string (uuid4) | |
| `created_at` | datetime | |
| `strategy_id` | string | e.g. `"sma_crossover_v1"` or `"llm_manual"` |
| `symbol` | string | OKX `instId`, e.g. `"BTC-USDT"` |
| `instrument_type` | `SPOT \| SWAP \| FUTURES \| OPTION` | |
| `side` | `buy \| sell` | |
| `order_type` | `market \| limit \| post_only \| fok \| ioc` | |
| `size` | string | decimal-as-string, never a float |
| `size_unit` | `base_ccy \| quote_ccy \| contracts` | |
| `price` | string? | required for `base_ccy` notional estimates |
| `leverage` | string? | |
| `rationale` | string | free-text justification |
| `confidence` | float? | 0..1 |
| `mode` | `simulation \| live` | must match `HELIO_MODE` for the session |
| `source` | `llm \| strategy \| manual` | |
| `metadata` | object | free-form |

## RiskDecision

| Field | Type |
|---|---|
| `decision_id` | string |
| `intent_id` | string |
| `evaluated_at` | datetime |
| `approved` | bool |
| `reasons` | string[] (always populated, even on approval) |
| `violated_rules` | string[] |
| `risk_config_hash` | string |
| `computed` | object |

## AccountState

Populated by Claude Code POSTing reshaped `account_get_balance` /
`account_get_positions` MCP output to `POST /state/account`.

`balances: Balance[]` (`ccy, avail, total`), `positions: Position[]`
(`instId, posSide, pos, avgPx, upl, lever?`), plus `mode`, `open_orders_count`,
`daily_realized_pnl_usd?`.

## MarketSnapshot

Reshaped `market_get_ticker` / `market_get_candles` MCP output:
`instId, as_of, last_price, candles: Candle[]` (`ts, o, h, l, c, vol`).

## LearningEvent

The unit stored by the learning engine: `intent`, `decision`,
`execution_result?` (from the MCP order response), `outcome?`.

## RiskConfig

See `backend/config/risk_config.example.yaml` — `allow_live` is the hard
live-trading gate; everything else is a numeric or list-based limit.

## GATE 2 (THINK) schemas — `backend/src/helio/schemas/thesis.py`

**TimeframeIndicators**: `timeframe` (`4H|1H|15m`), `as_of`, `candle_count`,
`price`, `ema20/50/200`, `atr`, `atr_pct`, `volume`, `volume_avg`,
`volume_ratio`, `swing_high`, `swing_low`, `price_change_pct` — all
decimal-as-string except `candle_count`. Computed by
`thesis/indicators.py::compute_indicators()`, never by an LLM.

**PreparedMarketState**: what `POST /thesis/prepare` returns —
`symbol`, `prepared_at`, `tf_4h/tf_1h/tf_15m: TimeframeIndicators`,
`regime` (`BULL_TREND|BEAR_TREND|RANGE|HIGH_VOLATILITY_UNCLEAR`),
`regime_reason`, `evidence: EvidenceItem[]` (`name, passed, detail,
hard_gate`), `candidate_action` (Helio's own reference BUY/WAIT — never the
final answer), `strategy="trend_breakout"`, `strategy_version="v1"`.

**Thesis**: assembled by the LLM and POSTed to `/thesis/submit` —
`decision_id`, `symbol`, `timestamp`, `regime`, `strategy`,
`strategy_version`, `action` (`BUY|WAIT`), `confidence` (float, `[0,1]`),
`thesis` (prose), `evidence: string[]` (prose bullets, distinct from
`PreparedMarketState.evidence`'s structured booleans), `invalidation?
{condition, price?}`, `target? {price?}`, `risk_reward?`, `market_state:
ThesisMarketStateEcho` — numbers the LLM must copy verbatim from the
`PreparedMarketState` it was given (`price, ema20_4h, ema50_4h, ema200_4h,
atr_1h, volume_ratio, swing_high_1h, swing_low_1h`).

**ThesisValidationResult**: `valid, errors[], warnings[]` — returned
alongside the thesis from `/thesis/submit`. See
`thesis/decision_quality.py` for the exact rules (regime contradiction,
unsupported-by-evidence BUY, missing invalidation, numeric hallucination
cross-check within a documented tolerance).

**CandleBundle**: input to `/thesis/prepare` — `symbol`,
`tf_4h/tf_1h/tf_15m: Candle[]` (reuses `schemas.market.Candle`).

**ThesisRecord**: what `/thesis/latest` and `/thesis/history` return —
`decision_id, logged_at, thesis, prepared_state, validation`.

## GATE 3 (PROTECT) schemas — `backend/src/helio/schemas/guard.py`

**GuardTradeIntent**: the normalized trade proposal a `GuardEngine` may
evaluate — `trade_intent_id`, `symbol`, `side` (`buy|sell`), `order_type`,
`instrument_type` (default `SPOT`), `leverage?`, `requested_notional`,
`requested_quantity`, `entry_price` (all decimal-as-string), `invalidation?
{condition, price?}`, `target? {price?}` (reuses `schemas.thesis.Invalidation`/
`Target`), `strategy`, `strategy_version`, `thesis_id` (links to a
`ThesisRecord.decision_id`), `confidence` (float, `[0,1]`), `timestamp`.

**GuardCheck**: `name, status (PASS|FAIL), reason` — one per rule in
`guard/rules.py`, always populated (even on PASS) for full auditability.

**GuardRiskSummary**: `requested_notional, max_allowed_notional,
estimated_loss?, risk_reward?` — computed by the engine regardless of the
final decision, for display/logging.

**GuardDecision**: `decision (APPROVE|REJECT), trade_intent_id, checks:
GuardCheck[], risk_summary, rejection_reasons: string[], policy_version,
evaluated_at`. A REJECT always carries at least one explicit reason; an
APPROVE means every check passed.

**GuardRecord**: what `/guard/latest`, `/guard/history`, and
`/guard/for-thesis/{id}` return — `trade_intent_id, logged_at, trade_intent,
decision`.
