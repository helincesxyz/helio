from __future__ import annotations

from helio.thesis.evidence import build_evidence, candidate_action
from helio.thesis.indicators import compute_indicators
from helio.thesis.regime import classify_regime


def _prepare(make_candles, tf_4h_trend="up", tf_1h_trend="up", tf_15m_trend="up", volume_spike_at=None):
    c4h = make_candles(n=300, trend=tf_4h_trend, volatility_pct=0.3, bar_minutes=240)
    c1h = make_candles(n=300, trend=tf_1h_trend, volatility_pct=0.3, bar_minutes=60, volume_spike_at=volume_spike_at)
    c15m = make_candles(n=300, trend=tf_15m_trend, volatility_pct=0.3, bar_minutes=15)
    ind_4h = compute_indicators(c4h, "4H")
    ind_1h = compute_indicators(c1h, "1H")
    ind_15m = compute_indicators(c15m, "15m")
    regime, _ = classify_regime(ind_4h)
    evidence = build_evidence(regime, ind_4h, ind_1h, ind_15m)
    return regime, evidence


def test_breakout_detected_all_hard_gates_pass(make_candles):
    regime, evidence = _prepare(make_candles, volume_spike_at=-1)
    assert candidate_action(regime, evidence) == "BUY"
    assert all(e.passed for e in evidence if e.hard_gate)


def test_breakout_rejected_due_to_volume(make_candles):
    regime, evidence = _prepare(make_candles, volume_spike_at=None)
    volume_evidence = next(e for e in evidence if e.name == "breakout_volume_confirmed_1h")
    assert volume_evidence.passed is False
    assert candidate_action(regime, evidence) == "WAIT"


def test_conflicting_timeframes_flagged(make_candles):
    # 4H trending up (bullish regime) but 1H/15m trending down: internally inconsistent.
    regime, evidence = _prepare(make_candles, tf_4h_trend="up", tf_1h_trend="down", tf_15m_trend="down")
    consistency = next(e for e in evidence if e.name == "timeframes_consistent")
    assert consistency.passed is False
    assert candidate_action(regime, evidence) == "WAIT"


def test_evidence_list_has_seven_named_items(make_candles):
    regime, evidence = _prepare(make_candles)
    names = {e.name for e in evidence}
    assert names == {
        "trend_structure_bullish_4h",
        "higher_high_structure_4h",
        "breakout_level_broken_or_approached_1h",
        "breakout_volume_confirmed_1h",
        "entry_confirmation_not_chasing_15m",
        "volatility_not_abnormal_4h",
        "timeframes_consistent",
    }
    hard_gate_names = {e.name for e in evidence if e.hard_gate}
    assert "higher_high_structure_4h" not in hard_gate_names
