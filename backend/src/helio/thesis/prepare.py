from __future__ import annotations

from helio.schemas.thesis import CandleBundle, EvidenceItem, PreparedMarketState, TimeframeIndicators
from helio.thesis.evidence import build_evidence, candidate_action
from helio.thesis.indicators import RawIndicators, compute_indicators
from helio.thesis.regime import classify_regime


def _to_schema(ind: RawIndicators, timeframe: str) -> TimeframeIndicators:
    return TimeframeIndicators(
        timeframe=timeframe,
        candle_count=ind.candle_count,
        price=str(ind.price),
        ema20=str(ind.ema20),
        ema50=str(ind.ema50),
        ema200=str(ind.ema200),
        atr=str(ind.atr),
        atr_pct=str(ind.atr_pct),
        volume=str(ind.volume),
        volume_avg=str(ind.volume_avg),
        volume_ratio=str(ind.volume_ratio),
        swing_high=str(ind.swing_high),
        swing_low=str(ind.swing_low),
        price_change_pct=str(ind.price_change_pct),
    )


def prepare_market_state(bundle: CandleBundle) -> PreparedMarketState:
    """The only place raw candles turn into a PreparedMarketState. Every
    number here is computed deterministically in Python — never by an LLM."""
    raw_4h = compute_indicators(bundle.tf_4h, "4H")
    raw_1h = compute_indicators(bundle.tf_1h, "1H")
    raw_15m = compute_indicators(bundle.tf_15m, "15m")

    regime, regime_reason = classify_regime(raw_4h)
    evidence = build_evidence(regime, raw_4h, raw_1h, raw_15m)
    action = candidate_action(regime, evidence)

    return PreparedMarketState(
        symbol=bundle.symbol,
        tf_4h=_to_schema(raw_4h, "4H"),
        tf_1h=_to_schema(raw_1h, "1H"),
        tf_15m=_to_schema(raw_15m, "15m"),
        regime=regime,
        regime_reason=regime_reason,
        evidence=[EvidenceItem(name=e.name, passed=e.passed, detail=e.detail, hard_gate=e.hard_gate) for e in evidence],
        candidate_action=action,
    )
