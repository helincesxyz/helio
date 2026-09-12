"""Deterministic 4H regime classification — no LLM/subjective judgment.

Threshold rationale (documented, not arbitrary):
- HIGH_VOL_ATR_PCT_THRESHOLD: normal BTC 4H ATR-as-%-of-price historically
  runs ~1-3%. >6% (roughly 2-3x typical) is a v1 heuristic ceiling for
  "abnormal" — flagged for recalibration once real trade history/backtesting
  exists, not claimed to be precisely optimal.
- RANGE_EMA_SPREAD_PCT_THRESHOLD: EMAs within 1% of each other are
  considered "bunched" (no meaningful separation to call a trend).

The volatility check runs FIRST, before trend structure: a violently
whipsawing market can transiently stack EMAs into a trend-looking shape,
and a market too chaotic to trust structure in should never be reported as
cleanly trending regardless of EMA order.
"""
from __future__ import annotations

from helio.thesis.indicators import LOOKBACK_WINDOW, RawIndicators

HIGH_VOL_ATR_PCT_THRESHOLD = 6.0
RANGE_EMA_SPREAD_PCT_THRESHOLD = 1.0

BULL_TREND = "BULL_TREND"
BEAR_TREND = "BEAR_TREND"
RANGE = "RANGE"
HIGH_VOLATILITY_UNCLEAR = "HIGH_VOLATILITY_UNCLEAR"


def classify_regime(ind_4h: RawIndicators) -> tuple[str, str]:
    """Returns (regime, regime_reason). regime_reason names the actual
    numbers used, for PreparedMarketState.regime_reason and debugging."""
    if ind_4h.atr_pct > HIGH_VOL_ATR_PCT_THRESHOLD:
        return (
            HIGH_VOLATILITY_UNCLEAR,
            f"4H ATR% {ind_4h.atr_pct:.2f}% exceeds high-volatility threshold "
            f"{HIGH_VOL_ATR_PCT_THRESHOLD}%",
        )

    if ind_4h.ema20 > ind_4h.ema50 > ind_4h.ema200 and ind_4h.price_change_pct > 0:
        return (
            BULL_TREND,
            f"4H EMA20 ({ind_4h.ema20:.2f}) > EMA50 ({ind_4h.ema50:.2f}) > EMA200 "
            f"({ind_4h.ema200:.2f}) with positive {LOOKBACK_WINDOW}-bar price "
            f"change ({ind_4h.price_change_pct:+.2f}%)",
        )

    if ind_4h.ema20 < ind_4h.ema50 < ind_4h.ema200 and ind_4h.price_change_pct < 0:
        return (
            BEAR_TREND,
            f"4H EMA20 ({ind_4h.ema20:.2f}) < EMA50 ({ind_4h.ema50:.2f}) < EMA200 "
            f"({ind_4h.ema200:.2f}) with negative {LOOKBACK_WINDOW}-bar price "
            f"change ({ind_4h.price_change_pct:+.2f}%)",
        )

    ema20_50_spread_pct = abs(ind_4h.ema20 - ind_4h.ema50) / ind_4h.ema50 * 100
    ema50_200_spread_pct = abs(ind_4h.ema50 - ind_4h.ema200) / ind_4h.ema200 * 100
    if ema20_50_spread_pct < RANGE_EMA_SPREAD_PCT_THRESHOLD and ema50_200_spread_pct < RANGE_EMA_SPREAD_PCT_THRESHOLD:
        return (
            RANGE,
            f"4H EMAs bunched within {RANGE_EMA_SPREAD_PCT_THRESHOLD}% of each other "
            f"(20/50 spread {ema20_50_spread_pct:.2f}%, 50/200 spread {ema50_200_spread_pct:.2f}%)",
        )

    return (
        HIGH_VOLATILITY_UNCLEAR,
        "4H EMA structure is mixed/ambiguous — neither a clean trend nor a tight range",
    )

