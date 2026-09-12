from __future__ import annotations

import pytest
from pydantic import ValidationError

from helio.schemas.guard import GuardTradeIntent, Invalidation, Target


def _valid_kwargs(**overrides) -> dict:
    defaults = dict(
        symbol="BTC-USDT",
        side="buy",
        order_type="market",
        requested_notional="50",
        requested_quantity="0.001",
        entry_price="50000",
        invalidation=Invalidation(condition="x", price="48500"),
        target=Target(price="53000"),
        strategy="trend_breakout",
        strategy_version="v1",
        thesis_id="abc-123",
        confidence=0.75,
    )
    defaults.update(overrides)
    return defaults


def test_valid_intent_parses():
    intent = GuardTradeIntent(**_valid_kwargs())
    assert intent.side == "buy"
    assert intent.instrument_type == "SPOT"


def test_malformed_missing_required_field_rejected():
    kwargs = _valid_kwargs()
    del kwargs["entry_price"]
    with pytest.raises(ValidationError):
        GuardTradeIntent(**kwargs)


def test_malformed_unknown_field_rejected():
    with pytest.raises(ValidationError):
        GuardTradeIntent(**_valid_kwargs(api_key="leaked"))


def test_malformed_wrong_type_rejected():
    with pytest.raises(ValidationError):
        GuardTradeIntent(**_valid_kwargs(confidence="very confident"))


@pytest.mark.parametrize("bad_confidence", [-0.1, 1.1, 5.0])
def test_confidence_out_of_range_rejected(bad_confidence):
    with pytest.raises(ValidationError):
        GuardTradeIntent(**_valid_kwargs(confidence=bad_confidence))


def test_futures_instrument_type_accepted_by_schema_but_will_be_rejected_by_rules():
    # Schema itself allows any known instrument_type literal; the guard
    # engine's check_spot_only rule is what actually rejects it (see
    # test_guard_rules.py) - this documents that split.
    intent = GuardTradeIntent(**_valid_kwargs(instrument_type="FUTURES", leverage="5"))
    assert intent.instrument_type == "FUTURES"
