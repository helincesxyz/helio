"""Deterministic evidence checklist for the trend_breakout v1 strategy.

Each item is a named, documented boolean gate. Six of the seven are "hard
gates" — used both to compute Helio's own reference `candidate_action` (see
`candidate_action()` below) and, downstream, by `decision_quality.py` to
flag an LLM-proposed BUY that the evidence doesn't actually support. Item 2
(higher-high structure) is supplementary only — useful context for the LLM,
not required for a valid breakout.

Threshold rationale:
- BREAKOUT_PROXIMITY_PCT: "breaks or approaches" a swing high means within
  0.5% below it or above it — close enough to matter, not requiring a full
  confirmed close above the level (that would make the setup lag badly).
- VOLUME_CONFIRM_RATIO: 1.3x the 20-bar average volume is a common,
  conservative "meaningfully above normal" heuristic for breakout volume.
- NOT_CHASING_PCT: the 15m confirmation candle should be within 1.0% of the
  1H breakout level — enough room to confirm the move without waiting for a
  full retest, but not so much that price has already run away.
"""
from __future__ import annotations

from dataclasses import dataclass

from helio.thesis.indicators import RawIndicators
from helio.thesis.regime import BEAR_TREND, BULL_TREND, HIGH_VOL_ATR_PCT_THRESHOLD

BREAKOUT_PROXIMITY_PCT = 0.5
VOLUME_CONFIRM_RATIO = 1.3
NOT_CHASING_PCT = 1.0


@dataclass
class EvidenceResult:
    name: str
    passed: bool
    detail: str
    hard_gate: bool


def _direction(ind: RawIndicators) -> str:
    if ind.ema20 > ind.ema50:
        return "up"
    if ind.ema20 < ind.ema50:
        return "down"
    return "flat"


def build_evidence(
    regime: str, ind_4h: RawIndicators, ind_1h: RawIndicators, ind_15m: RawIndicators
) -> list[EvidenceResult]:
    items: list[EvidenceResult] = []

    trend_bullish_4h = ind_4h.ema20 > ind_4h.ema50 > ind_4h.ema200
    items.append(
        EvidenceResult(
            name="trend_structure_bullish_4h",
            passed=trend_bullish_4h,
            detail=f"4H EMA20 {ind_4h.ema20:.2f} vs EMA50 {ind_4h.ema50:.2f} vs EMA200 {ind_4h.ema200:.2f}",
            hard_gate=True,
        )
    )

    items.append(
        EvidenceResult(
            name="higher_high_structure_4h",
            passed=ind_4h.higher_high,
            detail="current 20-bar 4H high vs prior 20-bar 4H high",
            hard_gate=False,
        )
    )

    breakout_threshold = ind_1h.swing_high * (1 - BREAKOUT_PROXIMITY_PCT / 100)
    breakout_ok = ind_1h.price >= breakout_threshold
    items.append(
        EvidenceResult(
            name="breakout_level_broken_or_approached_1h",
            passed=breakout_ok,
            detail=(
                f"1H price {ind_1h.price:.2f} vs swing high {ind_1h.swing_high:.2f} "
                f"(within {BREAKOUT_PROXIMITY_PCT}% required)"
            ),
            hard_gate=True,
        )
    )

    volume_ok = ind_1h.volume_ratio >= VOLUME_CONFIRM_RATIO
    items.append(
        EvidenceResult(
            name="breakout_volume_confirmed_1h",
            passed=volume_ok,
            detail=f"1H volume ratio {ind_1h.volume_ratio:.2f}x (need >= {VOLUME_CONFIRM_RATIO}x)",
            hard_gate=True,
        )
    )

    chase_pct = abs(ind_15m.price - ind_1h.swing_high) / ind_1h.swing_high * 100
    not_chasing = chase_pct <= NOT_CHASING_PCT
    items.append(
        EvidenceResult(
            name="entry_confirmation_not_chasing_15m",
            passed=not_chasing,
            detail=f"15m price is {chase_pct:.2f}% from the 1H breakout level (need <= {NOT_CHASING_PCT}%)",
            hard_gate=True,
        )
    )

    volatility_ok = ind_4h.atr_pct <= HIGH_VOL_ATR_PCT_THRESHOLD
    items.append(
        EvidenceResult(
            name="volatility_not_abnormal_4h",
            passed=volatility_ok,
            detail=f"4H ATR% {ind_4h.atr_pct:.2f}% (ceiling {HIGH_VOL_ATR_PCT_THRESHOLD}%)",
            hard_gate=True,
        )
    )

    regime_direction = "up" if regime == BULL_TREND else "down" if regime == BEAR_TREND else None
    dir_1h, dir_15m = _direction(ind_1h), _direction(ind_15m)
    consistent = regime_direction is None or (dir_1h != _opposite(regime_direction) and dir_15m != _opposite(regime_direction))
    items.append(
        EvidenceResult(
            name="timeframes_consistent",
            passed=consistent,
            detail=f"4H regime direction vs 1H ({dir_1h}) and 15m ({dir_15m}) EMA20/EMA50 direction",
            hard_gate=True,
        )
    )

    return items


def _opposite(direction: str) -> str:
    return "down" if direction == "up" else "up"


def candidate_action(regime: str, evidence: list[EvidenceResult]) -> str:
    """Helio's own deterministic reference decision — used only so
    decision_quality.py can flag an LLM-proposed BUY the evidence doesn't
    support. Never surfaced to the user as the actual action; the LLM
    decides that."""
    hard_gates_passed = all(e.passed for e in evidence if e.hard_gate)
    if regime == BULL_TREND and hard_gates_passed:
        return "BUY"
    return "WAIT"
