# Runbook: conversation bridge fulfillment

Helio's backend cannot reach OKX or an LLM on its own — only Claude Code's
current session can call the OKX Agent Trade Kit MCP tools (see
[ARCHITECTURE.md](../ARCHITECTURE.md)). The conversation bridge exists so
the UI can still feel like a live agent: the UI posts a request, Claude
Code (a human-initiated session, actively watching) fulfills it with
genuinely fresh data, and posts the structured result back. This is the
same credential-blind, LLM-blind-to-secrets pattern as every other gate —
just applied to the "answer a natural-language question" path instead of
"evaluate one trade."

**Every numerical claim in a response must trace to a real MCP response or
a real computed value from `thesis/indicators.py` / `guard/rules.py`.
Never invent a price, balance, APY, evidence item, or order state.**

## Polling loop

While a Claude Code session is driving a live demo:

1. `GET /conversation/requests?status=pending` — see what's waiting.
2. For each pending request, dispatch on `intent`:

### `GET_INTO_BTC`

1. Fetch **fresh** candles (4H/1H/15m — not reused from an earlier point in
   the session) via `market_get_candles`, and fresh account state via
   `account_get_balance` / `account_get_positions`.
2. `POST /thesis/prepare` with the reshaped candle bundle.
3. Write the qualitative thesis and `POST /thesis/submit`.
4. If `action == "BUY"`, build a `GuardTradeIntent` from the thesis and
   `POST /guard/evaluate` with the request's `risk_profile`.
5. `POST /conversation/requests/{id}/respond` with
   `{"kind": "thesis", "thesis_id": <decision_id>}`.
6. If the genuine answer is WAIT, respond with the same `thesis_id` anyway
   — WAIT is a first-class, honest answer, never suppressed or retried
   until a BUY appears.

### `OPTIMIZE_MONEY`

Same fresh BTC thesis fetch as above, plus one real Earn rate check
(`earn_get_lending_rate_history`). Assemble and respond with:
`{"kind": "allocation_comparison", "comparison": {"cash": ..., "earn": {"apy": ...}, "trade": {"action": ..., "confidence": ...}}}`.

### `OPTIMIZE_APY`

Call `earn_get_lending_rate_history` (and `onchain_earn_get_offers` if a
specific currency was mentioned) for real current offers. Apply the
request's `risk_profile` thresholds to filter/rank. Respond with
`{"kind": "apy_comparison", "comparison": {...}}`. **Never** calls
`earn_savings_purchase`, `earn_fixed_purchase`, `onchain_earn_purchase`, or
any other subscribe/redeem tool from this path — discovery only.

### `UNKNOWN`

Respond honestly: `{"kind": "unavailable", "message": "Helio doesn't have a workflow for that yet."}`.
Never guess an intent just to produce an answer.

## Rules

- `POST /conversation/requests/{id}/respond` is the **only** way an answer
  gets attached, and it fails closed: a request that's already
  `ANSWERED`/`FAILED` cannot be re-answered (409), and an unknown
  `request_id` is a 404. No double-answer, no silent overwrite.
- "Why?" follow-ups never reach this bridge — they're answered client-side
  from the already-loaded thesis (see `frontend/src/lib/summarize.ts`'s
  `explainWhy`).
- If fulfillment fails partway (an MCP call errors, a validation fails),
  respond with `{"kind": "error", "message": "<honest, specific reason>"}`
  rather than leaving the request PENDING forever or fabricating a result.
