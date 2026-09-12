from __future__ import annotations

from helio.thesis.indicators import compute_indicators
from helio.thesis.regime import BEAR_TREND, BULL_TREND, HIGH_VOLATILITY_UNCLEAR, RANGE, classify_regime


def test_classifies_bull_trend(make_candles):
    candles = make_candles(n=300, trend="up", volatility_pct=0.3)
    ind = compute_indicators(candles, "4H")
    regime, reason = classify_regime(ind)
    assert regime == BULL_TREND
    assert "EMA20" in reason


def test_classifies_bear_trend(make_candles):
    candles = make_candles(n=300, trend="down", volatility_pct=0.3)
    ind = compute_indicators(candles, "4H")
    regime, _ = classify_regime(ind)
    assert regime == BEAR_TREND


def test_classifies_range(make_candles):
    candles = make_candles(n=300, trend="flat", volatility_pct=0.3)
    ind = compute_indicators(candles, "4H")
    regime, _ = classify_regime(ind)
    assert regime == RANGE


def test_classifies_high_volatility_unclear(make_candles):
    # Large wicks relative to price with no net drift -> ATR% far above threshold.
    candles = make_candles(n=300, trend="flat", volatility_pct=4.0)
    ind = compute_indicators(candles, "4H")
    regime, reason = classify_regime(ind)
    assert regime == HIGH_VOLATILITY_UNCLEAR
    assert "ATR%" in reason


def test_high_volatility_overrides_apparent_trend(make_candles):
    # Even with an uptrend, extreme volatility should win the classification.
    candles = make_candles(n=300, trend="up", volatility_pct=5.0)
    ind = compute_indicators(candles, "4H")
    regime, _ = classify_regime(ind)
    assert regime == HIGH_VOLATILITY_UNCLEAR
