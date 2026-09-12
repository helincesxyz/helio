from __future__ import annotations

import pytest
from pydantic import ValidationError

from helio.schemas.account import AccountState
from helio.schemas.trade_intent import TradeIntent


def test_trade_intent_rejects_unknown_fields(make_intent):
    with pytest.raises(ValidationError):
        TradeIntent(
            strategy_id="x",
            symbol="BTC-USDT",
            instrument_type="SPOT",
            side="buy",
            order_type="market",
            size="1",
            size_unit="quote_ccy",
            rationale="x",
            mode="simulation",
            source="manual",
            api_key="should-not-be-accepted",
        )


def test_trade_intent_rejects_non_decimal_size():
    with pytest.raises(ValidationError):
        TradeIntent(
            strategy_id="x",
            symbol="BTC-USDT",
            instrument_type="SPOT",
            side="buy",
            order_type="market",
            size="not-a-number",
            size_unit="quote_ccy",
            rationale="x",
            mode="simulation",
            source="manual",
        )


def test_account_state_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        AccountState(mode="simulation", secret_key="nope")
