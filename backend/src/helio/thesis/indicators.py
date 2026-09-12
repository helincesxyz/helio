"""Deterministic technical indicators computed in Python — never delegated
to an LLM, so every number in a PreparedMarketState is exactly reproducible.

Minimum-candle-count rationale (documented once, applies to every constant
below): an EMA seeded with an SMA carries a residual bias from that seed for
a while. With smoothing factor `k`, the seed's influence after `m` further
bars is `(1-k)^m`. Requiring `m = 3 * period` for a standard EMA
(`k = 2/(period+1)`) drives that residual below `~2%` — small enough that
the reported value isn't meaningfully an artifact of the (somewhat
arbitrary) SMA-seeding convention. The same argument applies to ATR's
Wilder smoothing (`k = 1/period`), using `m = 4 * period` since Wilder
smoothing decays slower for the same period.

MIN_CANDLES_EMA200 is deliberately NOT the strict `3*200=600` — 600 4H
candles is 100 days and would make fetching data (and the live test) slow
and pagination-heavy. `250` is a pragmatic v1 floor (still comfortably more
than the period itself) — a documented tradeoff to revisit, not an oversight.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from helio.schemas.market import Candle

LOOKBACK_WINDOW = 20  # bars: volume average, swing hi/lo, price-change window

EMA_PERIODS = {"fast": 20, "medium": 50, "slow": 200}
MIN_CANDLES_EMA20 = 3 * EMA_PERIODS["fast"]      # 60
MIN_CANDLES_EMA50 = 3 * EMA_PERIODS["medium"]    # 150
MIN_CANDLES_EMA200 = 250                          # documented tradeoff, see module docstring

ATR_PERIOD = 14  # Wilder's original, industry-standard default
MIN_CANDLES_ATR14 = 60  # 4 * period = 56, rounded up to a clean 60

MIN_CANDLES_VOLUME = LOOKBACK_WINDOW + 1       # 21 (current bar + 20-bar average window)
MIN_CANDLES_SWING = LOOKBACK_WINDOW + 1        # 21
MIN_CANDLES_HIGHER_HIGH = 2 * LOOKBACK_WINDOW + 1  # 41 (current window + prior window)
MIN_CANDLES_PRICE_CHANGE = LOOKBACK_WINDOW + 1  # 21

# Applied uniformly to every timeframe (one shared code path, simpler to test);
# the cost of requiring this many bars even on 1H/15m is trivial (<=10.4 days of 1H data).
MIN_CANDLES_REQUIRED = max(
    MIN_CANDLES_EMA20,
    MIN_CANDLES_EMA50,
    MIN_CANDLES_EMA200,
    MIN_CANDLES_ATR14,
    MIN_CANDLES_HIGHER_HIGH,
)  # 250


class InsufficientDataError(ValueError):
    def __init__(self, timeframe: str, provided: int, required: int = MIN_CANDLES_REQUIRED):
        self.timeframe = timeframe
        self.provided = provided
        self.required = required
        super().__init__(
            f"{timeframe}: insufficient candles ({provided} provided, {required} required)"
        )


class InvalidIndicatorError(ValueError):
    def __init__(self, timeframe: str, field: str, value: float):
        self.timeframe = timeframe
        self.field = field
        self.value = value
        super().__init__(f"{timeframe}: computed indicator {field}={value!r} is NaN/inf/non-positive")


@dataclass
class RawIndicators:
    """Plain-float intermediate result — converted to decimal-as-string only
    at the schema boundary (see thesis/prepare.py)."""

    price: float
    ema20: float
    ema50: float
    ema200: float
    atr: float
    atr_pct: float
    volume: float
    volume_avg: float
    volume_ratio: float
    swing_high: float
    swing_low: float
    price_change_pct: float
    higher_high: bool
    candle_count: int


def _ema(values: list[float], period: int) -> float:
    k = 2 / (period + 1)
    seed = sum(values[:period]) / period
    ema = seed
    for v in values[period:]:
        ema = v * k + ema * (1 - k)
    return ema


def _atr(highs: list[float], lows: list[float], closes: list[float], period: int = ATR_PERIOD) -> float:
    trs: list[float] = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def compute_indicators(candles: list[Candle], timeframe: str) -> RawIndicators:
    """Compute every indicator from a chronologically-ordered candle list
    (oldest first, most recent last). Fails closed: raises rather than
    guessing when there isn't enough data or a computed value is invalid."""
    if len(candles) < MIN_CANDLES_REQUIRED:
        raise InsufficientDataError(timeframe, len(candles))

    closes = [float(c.c) for c in candles]
    highs = [float(c.h) for c in candles]
    lows = [float(c.l) for c in candles]
    volumes = [float(c.vol) for c in candles]

    price = closes[-1]
    ema20 = _ema(closes, EMA_PERIODS["fast"])
    ema50 = _ema(closes, EMA_PERIODS["medium"])
    ema200 = _ema(closes, EMA_PERIODS["slow"])
    atr = _atr(highs, lows, closes)
    atr_pct = atr / price * 100

    volume = volumes[-1]
    volume_avg = sum(volumes[-1 - LOOKBACK_WINDOW : -1]) / LOOKBACK_WINDOW
    volume_ratio = volume / volume_avg if volume_avg > 0 else math.inf

    swing_high = max(highs[-LOOKBACK_WINDOW:])
    swing_low = min(lows[-LOOKBACK_WINDOW:])

    prior_high = max(highs[-2 * LOOKBACK_WINDOW : -LOOKBACK_WINDOW])
    higher_high = swing_high > prior_high

    price_change_pct = (closes[-1] - closes[-1 - LOOKBACK_WINDOW]) / closes[-1 - LOOKBACK_WINDOW] * 100

    result = RawIndicators(
        price=price,
        ema20=ema20,
        ema50=ema50,
        ema200=ema200,
        atr=atr,
        atr_pct=atr_pct,
        volume=volume,
        volume_avg=volume_avg,
        volume_ratio=volume_ratio,
        swing_high=swing_high,
        swing_low=swing_low,
        price_change_pct=price_change_pct,
        higher_high=higher_high,
        candle_count=len(candles),
    )

    for field_name in ("price", "ema20", "ema50", "ema200", "atr", "atr_pct", "volume_ratio"):
        value = getattr(result, field_name)
        if math.isnan(value) or math.isinf(value):
            raise InvalidIndicatorError(timeframe, field_name, value)
    if price <= 0:
        raise InvalidIndicatorError(timeframe, "price", price)

    return result
