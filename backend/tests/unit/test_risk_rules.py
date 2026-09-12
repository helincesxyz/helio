from __future__ import annotations

from helio.schemas.account import AccountState, Balance, Position
from helio.risk import rules


def test_sim_vs_live_gate_rejects_live_by_default(make_intent, make_account, risk_config):
    intent = make_intent(mode="live")
    result = rules.check_sim_vs_live_gate(intent, make_account(), risk_config)
    assert result.passed is False


def test_sim_vs_live_gate_allows_live_when_configured(make_intent, make_account, risk_config):
    risk_config.allow_live = True
    intent = make_intent(mode="live")
    result = rules.check_sim_vs_live_gate(intent, make_account(), risk_config)
    assert result.passed is True


def test_sim_vs_live_gate_allows_simulation(make_intent, make_account, risk_config):
    intent = make_intent(mode="simulation")
    result = rules.check_sim_vs_live_gate(intent, make_account(), risk_config)
    assert result.passed is True


def test_allowed_instrument_type_rejects_unlisted(make_intent, make_account, risk_config):
    intent = make_intent(instrument_type="FUTURES")
    result = rules.check_allowed_instrument_type(intent, make_account(), risk_config)
    assert result.passed is False


def test_allowed_instrument_rejects_unlisted_symbol(make_intent, make_account, risk_config):
    intent = make_intent(symbol="DOGE-USDT")
    result = rules.check_allowed_instrument(intent, make_account(), risk_config)
    assert result.passed is False


def test_allowed_instrument_allows_listed_symbol(make_intent, make_account, risk_config):
    intent = make_intent(symbol="ETH-USDT")
    result = rules.check_allowed_instrument(intent, make_account(), risk_config)
    assert result.passed is True


def test_max_order_notional_rejects_over_limit(make_intent, make_account, risk_config):
    intent = make_intent(size="1000", size_unit="quote_ccy")
    result = rules.check_max_order_notional(intent, make_account(), risk_config)
    assert result.passed is False


def test_max_order_notional_allows_under_limit(make_intent, make_account, risk_config):
    intent = make_intent(size="50", size_unit="quote_ccy")
    result = rules.check_max_order_notional(intent, make_account(), risk_config)
    assert result.passed is True


def test_max_order_notional_fails_closed_without_price(make_intent, make_account, risk_config):
    intent = make_intent(size="1", size_unit="base_ccy", price=None)
    result = rules.check_max_order_notional(intent, make_account(), risk_config)
    assert result.passed is False


def test_max_position_size_accounts_for_existing_position(make_intent, make_account, risk_config):
    account = make_account(positions=[Position(instId="BTC-USDT", posSide="long", pos="0.01", avgPx="45000", upl="0")])
    intent = make_intent(size="100", size_unit="quote_ccy")
    result = rules.check_max_position_size(intent, account, risk_config)
    # existing 0.01 * 45000 = 450, + 100 = 550 > max_position_size_usd (500)
    assert result.passed is False


def test_max_open_positions_rejects_new_symbol_over_limit(make_intent, make_account, risk_config):
    account = make_account(
        positions=[
            Position(instId="BTC-USDT", posSide="long", pos="0.01", avgPx="45000", upl="0"),
            Position(instId="ETH-USDT", posSide="long", pos="1", avgPx="3000", upl="0"),
        ]
    )
    intent = make_intent(symbol="ETH-USDT", size="10")  # not a new symbol, should pass
    result = rules.check_max_open_positions(intent, account, risk_config)
    assert result.passed is True


def test_max_open_positions_rejects_third_new_symbol(make_intent, make_account, risk_config):
    account = make_account(
        positions=[
            Position(instId="BTC-USDT", posSide="long", pos="0.01", avgPx="45000", upl="0"),
            Position(instId="ETH-USDT", posSide="long", pos="1", avgPx="3000", upl="0"),
        ]
    )
    intent = make_intent(symbol="SOL-USDT", size="10")  # risk_config fixture caps at 2 open positions
    result = rules.check_max_open_positions(intent, account, risk_config)
    assert result.passed is False


def test_max_leverage_rejects_over_limit(make_intent, make_account, risk_config):
    intent = make_intent(leverage="5")
    result = rules.check_max_leverage(intent, make_account(), risk_config)
    assert result.passed is False


def test_max_leverage_allows_under_limit(make_intent, make_account, risk_config):
    intent = make_intent(leverage="2")
    result = rules.check_max_leverage(intent, make_account(), risk_config)
    assert result.passed is True


def test_max_leverage_allows_none(make_intent, make_account, risk_config):
    intent = make_intent(leverage=None)
    result = rules.check_max_leverage(intent, make_account(), risk_config)
    assert result.passed is True


def test_max_daily_loss_rejects_when_limit_reached(make_intent, make_account, risk_config):
    account = make_account(daily_realized_pnl_usd="-60")
    result = rules.check_max_daily_loss(make_intent(), account, risk_config)
    assert result.passed is False


def test_max_daily_loss_allows_when_under_limit(make_intent, make_account, risk_config):
    account = make_account(daily_realized_pnl_usd="-10")
    result = rules.check_max_daily_loss(make_intent(), account, risk_config)
    assert result.passed is True


def test_exposure_cap_rejects_when_over_cap(make_intent, make_account, risk_config):
    # equity 1000, cap 20% = 200; existing 150 + new 100 = 250 > 200
    account = make_account(
        balances=[Balance(ccy="USDT", avail="1000", total="1000")],
        positions=[Position(instId="BTC-USDT", posSide="long", pos="0.01", avgPx="15000", upl="0")],
    )
    intent = make_intent(size="100", size_unit="quote_ccy")
    result = rules.check_exposure_cap(intent, account, risk_config)
    assert result.passed is False


def test_exposure_cap_fails_closed_without_equity(make_intent, risk_config):
    account = AccountState(mode="simulation", balances=[], positions=[])
    result = rules.check_exposure_cap(make_intent(), account, risk_config)
    assert result.passed is False
