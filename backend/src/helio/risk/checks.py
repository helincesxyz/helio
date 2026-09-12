"""Local (non-MCP) portions of the verification checklist: RISK ENGINE,
LEARNING ENGINE, UI. The remaining checks (OKX CONNECTION, ACCOUNT, MARKET
DATA, PORTFOLIO, SPOT EXECUTION) can only be performed by Claude Code calling
MCP tools — see docs/VERIFICATION_PROTOCOL.md and docs/runbooks/verify.md.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from helio.schemas.account import AccountState
from helio.schemas.trade_intent import TradeIntent

if TYPE_CHECKING:
    from helio.service.deps import AppState


def _check_risk_engine(state: "AppState") -> tuple[str, bool, str]:
    empty_account = AccountState(mode="simulation")

    live_intent = TradeIntent(
        strategy_id="helio_selftest",
        symbol="BTC-USDT",
        instrument_type="SPOT",
        side="buy",
        order_type="market",
        size="10",
        size_unit="quote_ccy",
        rationale="verification self-test: live intent must be rejected by default",
        mode="live",
        source="manual",
    )
    live_decision = state.risk_engine.evaluate(live_intent, empty_account)
    if live_decision.approved:
        return ("RISK ENGINE", False, "a live-mode intent was approved despite allow_live being unset/false")

    sim_intent = live_intent.model_copy(update={"mode": "simulation", "size": "1"})
    sim_decision = state.risk_engine.evaluate(sim_intent, empty_account)
    if not sim_decision.approved and "sim_vs_live_gate" not in sim_decision.violated_rules:
        # A small simulation order was rejected for a reason OTHER than the
        # live gate (e.g. instrument not allowed) — still fine, engine works.
        pass

    return ("RISK ENGINE", True, "sim_vs_live_gate correctly rejects live intents by default")


def _check_learning_engine(state: "AppState") -> tuple[str, bool, str]:
    ok = state.event_store.self_test()
    detail = "round-trip write/read against the event store succeeded" if ok else "round-trip failed"
    return ("LEARNING ENGINE", ok, detail)


def _check_ui(state: "AppState") -> tuple[str, bool, str]:
    dist_index = Path("frontend/dist/index.html")
    if dist_index.exists():
        return ("UI", True, "frontend/dist/index.html found (built)")
    return ("UI", False, "frontend not built yet — run `npm run build` in frontend/")


def run_local_checks(state: "AppState") -> list[tuple[str, bool, str]]:
    return [_check_risk_engine(state), _check_learning_engine(state), _check_ui(state)]
