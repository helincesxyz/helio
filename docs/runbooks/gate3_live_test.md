# Runbook: GATE 3 live test

Copy-paste this as a prompt to Claude Code, with Helio's service running
(`make serve` from the repo root).

**This must never call any order-placement, order-cancellation,
order-amendment, or transfer/withdrawal MCP tool. Read-only only — no
orders may be submitted.**

---

> Run the GATE 3 demo against the current real account state, read-only:
>
> 1. Fetch current account balance and positions for BTC-USDT via
>    `account_get_balance` / `account_get_positions` (read-only MCP calls).
> 2. Run `python3 scripts/risk_demo.py` to exercise both an APPROVED and a
>    REJECTED trade intent against the guard engine.
> 3. Separately, evaluate one real trade intent against the real account
>    state you fetched in step 1 via `POST /guard/evaluate`, linked to a
>    real thesis from a GATE 2 run.
> 4. Confirm via `pytest` (backend/) that the full GATE 3 test suite passes.
> 5. Confirm that at no point was `spot_place_order`, `spot_cancel_order`,
>    `spot_amend_order`, `account_transfer`, or any other execution/transfer
>    MCP tool called.
>
> Report back in exactly this format:
> ```
> GATE 3: PASS | FAIL
> Tests: <N> passed
> Approved scenarios: <list>
> Rejected scenarios: <list>
> Execution tools called: none
> Example approved intent: <summary>
> Example rejected intent: <summary + reasons>
> ```

---

`GATE 3: PASS` requires: the full pytest suite passes, the demo produces
both an APPROVE and a REJECT against real or realistic data, the real
account state was read (not fabricated), and no execution-tool MCP call
was made anywhere in the session.
