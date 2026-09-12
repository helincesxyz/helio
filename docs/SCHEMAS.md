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
