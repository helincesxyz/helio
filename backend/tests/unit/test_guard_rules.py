from __future__ import annotations

from datetime import datetime, timedelta, timezone

from helio.guard import rules
from helio.guard.context import GuardContext


def _ctx(thesis_record=None, account=None, is_duplicate=False, now=None):
    return GuardContext(account=account, thesis_record=thesis_record, is_duplicate=is_duplicate, now=now)


def test_allowed_symbol_rejects_eth(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis, symbol="ETH-USDT")
    result = rules.check_allowed_symbol(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_spot_only_rejects_futures(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis, instrument_type="FUTURES", leverage="5")
    result = rules.check_spot_only(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_no_leverage_rejects_leveraged(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis, leverage="5")
    result = rules.check_no_leverage(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_no_short_rejects_sell(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis, side="sell")
    result = rules.check_no_short(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_max_position_rejects_when_already_open(make_guard_intent, make_thesis_record, make_account, guard_config):
    from helio.schemas.account import Position

    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis)
    account = make_account(positions=[Position(instId="BTC-USDT", posSide="long", pos="0.01", avgPx="50000", upl="0")])
    result = rules.check_max_position(intent, _ctx(thesis, account), guard_config)
    assert result.status == "FAIL"


def test_max_position_allows_when_no_open_position(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis)
    result = rules.check_max_position(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "PASS"


def test_max_notional_rejects_oversized_trade(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis, requested_notional="10000")
    result = rules.check_max_notional(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_daily_loss_rejects_when_limit_reached(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis)
    account = make_account(daily_realized_pnl_usd="-60")
    result = rules.check_daily_loss(intent, _ctx(thesis, account), guard_config)
    assert result.status == "FAIL"


def test_daily_loss_rejects_when_missing(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis)
    account = make_account(daily_realized_pnl_usd=None)
    result = rules.check_daily_loss(intent, _ctx(thesis, account), guard_config)
    assert result.status == "FAIL"


def test_exposure_rejects_when_over_cap(make_guard_intent, make_thesis_record, make_account, guard_config):
    from helio.schemas.account import Balance, Position

    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis, requested_notional="100")
    # existing 0.003*50000=$150 + requested $100 = $250 / $1000 equity = 25% > 20% cap
    account = make_account(
        balances=[Balance(ccy="USDT", avail="1000", total="1000")],
        positions=[Position(instId="BTC-USDT", posSide="long", pos="0.003", avgPx="50000", upl="0")],
    )
    result = rules.check_exposure(intent, _ctx(thesis, account), guard_config)
    assert result.status == "FAIL"


def test_invalidation_missing_rejected(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis, invalidation=None)
    result = rules.check_invalidation_valid(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_invalid_stop_above_entry_rejected(make_guard_intent, make_thesis_record, make_account, guard_config):
    from helio.schemas.guard import Invalidation

    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis, invalidation=Invalidation(condition="x", price="51000"))
    result = rules.check_invalidation_valid(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_risk_reward_too_low_rejected(make_guard_intent, make_thesis_record, make_account, guard_config):
    from helio.schemas.guard import Invalidation, Target

    thesis = make_thesis_record()
    # risk = 50000-49000=1000, reward=50500-50000=500, rr=0.5 < 1.5
    intent = make_guard_intent(
        thesis_record=thesis,
        invalidation=Invalidation(condition="x", price="49000"),
        target=Target(price="50500"),
    )
    result = rules.check_risk_reward(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_risk_reward_zero_risk_fails_closed(make_guard_intent, make_thesis_record, make_account, guard_config):
    from helio.schemas.guard import Invalidation, Target

    thesis = make_thesis_record()
    intent = make_guard_intent(
        thesis_record=thesis,
        entry_price="50000",
        invalidation=Invalidation(condition="x", price="50000"),  # zero risk distance
        target=Target(price="53000"),
    )
    result = rules.check_risk_reward(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_market_data_stale_rejected(make_guard_intent, make_thesis_record, make_account, guard_config):
    stale_time = datetime.now(timezone.utc) - timedelta(hours=2)
    thesis = make_thesis_record(prepared_at=stale_time)
    intent = make_guard_intent(thesis_record=thesis)
    result = rules.check_market_data_fresh(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_market_data_fresh_passes(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis)
    result = rules.check_market_data_fresh(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "PASS"


def test_account_state_missing_rejected(make_guard_intent, make_thesis_record, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis)
    result = rules.check_account_state_verifiable(intent, _ctx(thesis, None), guard_config)
    assert result.status == "FAIL"


def test_thesis_not_found_rejected(make_guard_intent, make_account, guard_config):
    intent = make_guard_intent(thesis_id="does-not-exist")
    result = rules.check_thesis_found(intent, _ctx(None, make_account()), guard_config)
    assert result.status == "FAIL"


def test_thesis_wait_action_rejected(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record(action="WAIT")
    intent = make_guard_intent(thesis_record=thesis)
    result = rules.check_thesis_not_wait(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_thesis_invalid_validation_rejected(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record(valid=False, validation_errors=["some hallucination"])
    intent = make_guard_intent(thesis_record=thesis)
    result = rules.check_thesis_valid(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_duplicate_rejected(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis)
    result = rules.check_duplicate(intent, _ctx(thesis, make_account(), is_duplicate=True), guard_config)
    assert result.status == "FAIL"


def test_quantity_precision_rejects_non_multiple(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis, requested_quantity="0.0000000015")  # not a lot-size multiple
    result = rules.check_quantity_precision(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_quantity_below_minimum_rejected(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis, requested_quantity="0.000001")  # below minSz 0.00001
    result = rules.check_quantity_minimum(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_confidence_below_threshold_rejected(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record(confidence=0.3)
    intent = make_guard_intent(thesis_record=thesis, confidence=0.3)
    result = rules.check_min_confidence(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_confidence_mismatch_with_thesis_rejected(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record(confidence=0.75)
    intent = make_guard_intent(thesis_record=thesis, confidence=0.9)  # tampered
    result = rules.check_confidence_matches_thesis(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_thesis_symbol_mismatch_rejected(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record(symbol="BTC-USDT")
    intent = make_guard_intent(thesis_record=thesis, symbol="BTC-USDT")
    intent.symbol = "ETH-USDT"  # simulate a mismatched intent after construction
    result = rules.check_thesis_symbol_matches(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_well_formed_rejects_negative_notional(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis, requested_notional="-10")
    result = rules.check_well_formed(intent, _ctx(thesis, make_account()), guard_config)
    assert result.status == "FAIL"


def test_valid_intent_passes_every_rule(make_guard_intent, make_thesis_record, make_account, guard_config):
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis)
    ctx = _ctx(thesis, make_account())
    for rule in rules.ALL_RULES:
        result = rule(intent, ctx, guard_config)
        assert result.status == "PASS", f"{rule.__name__} unexpectedly failed: {result.reason}"
