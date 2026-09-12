from __future__ import annotations

from helio.guard.context import GuardContext
from helio.guard.engine import GuardEngine
from helio.schemas.account import Position
from helio.schemas.guard import Invalidation, Target


def test_valid_conservative_trade_is_approved(make_guard_intent, make_thesis_record, make_account, guard_config):
    engine = GuardEngine(guard_config)
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis)
    ctx = GuardContext(account=make_account(), thesis_record=thesis, is_duplicate=False)

    decision = engine.evaluate(intent, ctx)

    assert decision.decision == "APPROVE"
    assert decision.rejection_reasons == []
    assert all(c.status == "PASS" for c in decision.checks)
    assert decision.policy_version == guard_config.policy_version


def test_wait_thesis_is_rejected(make_guard_intent, make_thesis_record, make_account, guard_config):
    engine = GuardEngine(guard_config)
    thesis = make_thesis_record(action="WAIT")
    intent = make_guard_intent(thesis_record=thesis)
    ctx = GuardContext(account=make_account(), thesis_record=thesis, is_duplicate=False)

    decision = engine.evaluate(intent, ctx)

    assert decision.decision == "REJECT"
    assert any("WAIT" in r for r in decision.rejection_reasons)


def test_malicious_multi_violation_intent_rejects_with_every_reason(
    make_guard_intent, make_thesis_record, make_account, guard_config
):
    """The single most important test: an intent that violates almost every
    rule at once must be rejected, and every applicable violation must be
    identified — not just the first one encountered."""
    engine = GuardEngine(guard_config)
    thesis = make_thesis_record(action="BUY", confidence=0.75)
    intent = make_guard_intent(
        thesis_record=thesis,
        symbol="ETH-USDT",  # wrong symbol
        instrument_type="FUTURES",  # not spot
        leverage="10",  # leveraged
        side="sell",  # shorting
        requested_notional="100000",  # way over max
        requested_quantity="0.0000000015",  # bad precision
        entry_price="50000",
        invalidation=None,  # missing invalidation
        target=Target(price="50100"),
        confidence=0.05,  # below min_confidence
    )
    account = make_account(daily_realized_pnl_usd="-1000")  # blown daily loss limit
    ctx = GuardContext(account=account, thesis_record=thesis, is_duplicate=True)  # also a duplicate

    decision = engine.evaluate(intent, ctx)

    assert decision.decision == "REJECT"
    failed_names = {c.name for c in decision.checks if c.status == "FAIL"}
    assert "allowed_symbol" in failed_names
    assert "spot_only" in failed_names
    assert "no_leverage" in failed_names
    assert "no_short" in failed_names
    assert "max_notional" in failed_names
    assert "invalidation_defined" in failed_names
    assert "quantity_precision" in failed_names
    assert "min_confidence" in failed_names
    assert "confidence_matches_thesis" in failed_names
    assert "daily_loss_limit" in failed_names
    assert "not_duplicate" in failed_names
    assert "thesis_symbol_matches" in failed_names
    # every failure must have an explicit, non-empty reason
    assert all(c.reason.strip() for c in decision.checks if c.status == "FAIL")
    assert len(decision.rejection_reasons) == len(failed_names)


def test_unknown_risk_condition_fails_closed_instead_of_crashing(
    make_guard_intent, make_thesis_record, make_account, guard_config
):
    """A garbage/unparseable position value should never crash the engine
    into an uncaught exception (which could be mishandled upstream as an
    approval) - it must surface as a FAIL and an overall REJECT."""
    engine = GuardEngine(guard_config)
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis)
    account = make_account(
        positions=[Position(instId="BTC-USDT", posSide="long", pos="not-a-number", avgPx="50000", upl="0")]
    )
    ctx = GuardContext(account=account, thesis_record=thesis, is_duplicate=False)

    decision = engine.evaluate(intent, ctx)

    assert decision.decision == "REJECT"
    unknown_condition_checks = [c for c in decision.checks if "unknown risk condition" in c.reason]
    assert len(unknown_condition_checks) >= 1


def test_risk_summary_reflects_requested_values(make_guard_intent, make_thesis_record, make_account, guard_config):
    engine = GuardEngine(guard_config)
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis)
    ctx = GuardContext(account=make_account(), thesis_record=thesis, is_duplicate=False)

    decision = engine.evaluate(intent, ctx)

    assert decision.risk_summary.requested_notional == 50.0
    assert decision.risk_summary.max_allowed_notional == guard_config.max_notional_per_trade_usd
    assert decision.risk_summary.risk_reward is not None
    assert decision.risk_summary.risk_reward > 0
