from __future__ import annotations

import pytest

from helio.thesis.indicators import InsufficientDataError, MIN_CANDLES_REQUIRED, compute_indicators


def test_insufficient_candles_raises(make_candles):
    candles = make_candles(n=MIN_CANDLES_REQUIRED - 1, trend="flat")
    with pytest.raises(InsufficientDataError):
        compute_indicators(candles, "4H")


def test_sufficient_candles_computes_all_fields(make_candles):
    candles = make_candles(n=MIN_CANDLES_REQUIRED, trend="up")
    result = compute_indicators(candles, "4H")
    assert result.price > 0
    assert result.ema20 > 0
    assert result.ema50 > 0
    assert result.ema200 > 0
    assert result.atr > 0
    assert result.candle_count == MIN_CANDLES_REQUIRED


def test_uptrend_produces_stacked_emas_and_positive_change(make_candles):
    candles = make_candles(n=300, trend="up")
    result = compute_indicators(candles, "4H")
    assert result.ema20 > result.ema50 > result.ema200
    assert result.price_change_pct > 0


def test_downtrend_produces_stacked_emas_and_negative_change(make_candles):
    candles = make_candles(n=300, trend="down")
    result = compute_indicators(candles, "4H")
    assert result.ema20 < result.ema50 < result.ema200
    assert result.price_change_pct < 0


def test_flat_series_has_near_zero_ema_spread(make_candles):
    candles = make_candles(n=300, trend="flat", volatility_pct=0.1)
    result = compute_indicators(candles, "4H")
    assert result.ema20 == pytest.approx(result.ema200, rel=1e-6)


def test_volume_spike_increases_volume_ratio(make_candles):
    spiked = make_candles(n=300, trend="up", volume_spike_at=-1)
    flat_volume = make_candles(n=300, trend="up", volume_spike_at=None)
    spiked_result = compute_indicators(spiked, "1H")
    flat_result = compute_indicators(flat_volume, "1H")
    assert spiked_result.volume_ratio > flat_result.volume_ratio
    assert spiked_result.volume_ratio >= 1.3
    assert flat_result.volume_ratio == pytest.approx(1.0, abs=0.05)
