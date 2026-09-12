from __future__ import annotations

from helio.schemas.thesis import CandleBundle, Invalidation, Thesis, ThesisMarketStateEcho
from helio.thesis.decision_quality import validate
from helio.thesis.prepare import prepare_market_state


def _prepared(make_candles, tf_4h_trend="up", tf_1h_trend="up", tf_15m_trend="up", volume_spike_at=-1):
    bundle = CandleBundle(
        symbol="BTC-USDT",
        tf_4h=make_candles(n=300, trend=tf_4h_trend, volatility_pct=0.3, bar_minutes=240),
        tf_1h=make_candles(n=300, trend=tf_1h_trend, volatility_pct=0.3, bar_minutes=60, volume_spike_at=volume_spike_at),
        tf_15m=make_candles(n=300, trend=tf_15m_trend, volatility_pct=0.3, bar_minutes=15),
    )
    return prepare_market_state(bundle)


def _echo_from(state) -> ThesisMarketStateEcho:
    return ThesisMarketStateEcho(
        price=state.tf_15m.price,
        ema20_4h=state.tf_4h.ema20,
        ema50_4h=state.tf_4h.ema50,
        ema200_4h=state.tf_4h.ema200,
        atr_1h=state.tf_1h.atr,
        volume_ratio=state.tf_1h.volume_ratio,
        swing_high_1h=state.tf_1h.swing_high,
        swing_low_1h=state.tf_1h.swing_low,
    )


def test_valid_buy_thesis_accepted(make_candles):
    state = _prepared(make_candles, volume_spike_at=-1)
    assert state.regime == "BULL_TREND"
    thesis = Thesis(
        symbol=state.symbol,
        regime=state.regime,
        action="BUY",
        confidence=0.8,
        thesis="Breakout confirmed with volume.",
        evidence=[e.detail for e in state.evidence],
        invalidation=Invalidation(condition="Close back below the 1H swing high", price=state.tf_1h.swing_low),
        market_state=_echo_from(state),
    )
    result = validate(thesis, state)
    assert result.valid is True
    assert result.errors == []


def test_valid_wait_thesis_accepted_with_no_invalidation(make_candles):
    state = _prepared(make_candles, tf_4h_trend="flat", tf_1h_trend="flat", tf_15m_trend="flat", volume_spike_at=None)
    assert state.regime == "RANGE"
    thesis = Thesis(
        symbol=state.symbol,
        regime=state.regime,
        action="WAIT",
        confidence=0.3,
        thesis="No setup in a ranging market.",
        evidence=[e.detail for e in state.evidence],
        invalidation=None,
        market_state=_echo_from(state),
    )
    result = validate(thesis, state)
    assert result.valid is True
    assert result.errors == []


def test_buy_without_invalidation_rejected(make_candles):
    state = _prepared(make_candles, volume_spike_at=-1)
    thesis = Thesis(
        symbol=state.symbol,
        regime=state.regime,
        action="BUY",
        confidence=0.8,
        thesis="Breakout confirmed.",
        evidence=[e.detail for e in state.evidence],
        invalidation=None,
        market_state=_echo_from(state),
    )
    result = validate(thesis, state)
    assert result.valid is False
    assert any("invalidation" in e for e in result.errors)


def test_buy_rejected_due_to_failed_volume_gate(make_candles):
    state = _prepared(make_candles, volume_spike_at=None)  # no volume confirmation
    thesis = Thesis(
        symbol=state.symbol,
        regime=state.regime,
        action="BUY",
        confidence=0.8,
        thesis="Breakout attempted without volume confirmation.",
        evidence=[e.detail for e in state.evidence],
        invalidation=Invalidation(condition="Below swing low", price=state.tf_1h.swing_low),
        market_state=_echo_from(state),
    )
    result = validate(thesis, state)
    assert result.valid is False
    assert any("breakout_volume_confirmed_1h" in e for e in result.errors)


def test_buy_rejected_when_regime_is_bear_trend(make_candles):
    state = _prepared(make_candles, tf_4h_trend="down", tf_1h_trend="down", tf_15m_trend="down")
    assert state.regime == "BEAR_TREND"
    thesis = Thesis(
        symbol=state.symbol,
        regime=state.regime,
        action="BUY",
        confidence=0.9,
        thesis="Buying into a downtrend.",
        evidence=[e.detail for e in state.evidence],
        invalidation=Invalidation(condition="Below swing low", price=state.tf_1h.swing_low),
        market_state=_echo_from(state),
    )
    result = validate(thesis, state)
    assert result.valid is False
    assert any("contradicts deterministic regime" in e for e in result.errors)


def test_hallucinated_numerical_value_rejected(make_candles):
    state = _prepared(make_candles, volume_spike_at=-1)
    echo = _echo_from(state)
    echo.price = str(float(echo.price) * 1.5)  # fabricated, well outside tolerance
    thesis = Thesis(
        symbol=state.symbol,
        regime=state.regime,
        action="WAIT",
        confidence=0.5,
        thesis="Some reasoning with a made-up price.",
        evidence=[e.detail for e in state.evidence],
        market_state=echo,
    )
    result = validate(thesis, state)
    assert result.valid is False
    assert any("possible hallucination" in e for e in result.errors)


def test_thesis_regime_mismatch_rejected(make_candles):
    state = _prepared(make_candles, volume_spike_at=-1)
    thesis = Thesis(
        symbol=state.symbol,
        regime="RANGE",  # doesn't match the computed BULL_TREND
        action="WAIT",
        confidence=0.5,
        thesis="Mislabeled regime.",
        evidence=[e.detail for e in state.evidence],
        market_state=_echo_from(state),
    )
    result = validate(thesis, state)
    assert result.valid is False
    assert any("does not match Helio-computed regime" in e for e in result.errors)
