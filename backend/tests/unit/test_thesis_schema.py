from __future__ import annotations

import pytest
from pydantic import ValidationError

from helio.schemas.thesis import Thesis, ThesisMarketStateEcho


def _valid_kwargs(**overrides) -> dict:
    defaults = dict(
        symbol="BTC-USDT",
        regime="BULL_TREND",
        action="WAIT",
        confidence=0.5,
        thesis="Some reasoning.",
        evidence=["some evidence"],
        market_state=ThesisMarketStateEcho(),
    )
    defaults.update(overrides)
    return defaults


def test_valid_thesis_parses():
    thesis = Thesis(**_valid_kwargs())
    assert thesis.action == "WAIT"


def test_malformed_thesis_missing_required_field_rejected():
    kwargs = _valid_kwargs()
    del kwargs["thesis"]
    with pytest.raises(ValidationError):
        Thesis(**kwargs)


def test_malformed_thesis_unknown_field_rejected():
    with pytest.raises(ValidationError):
        Thesis(**_valid_kwargs(api_key="leaked"))


def test_malformed_thesis_wrong_type_rejected():
    with pytest.raises(ValidationError):
        Thesis(**_valid_kwargs(confidence="high"))


@pytest.mark.parametrize("bad_confidence", [-0.01, 1.01, 2.0, -5.0])
def test_confidence_out_of_range_rejected(bad_confidence):
    with pytest.raises(ValidationError):
        Thesis(**_valid_kwargs(confidence=bad_confidence))


@pytest.mark.parametrize("good_confidence", [0.0, 0.5, 1.0])
def test_confidence_in_range_accepted(good_confidence):
    thesis = Thesis(**_valid_kwargs(confidence=good_confidence))
    assert thesis.confidence == good_confidence
