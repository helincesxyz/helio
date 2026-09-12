"""Validates an LLM-assembled Thesis against the PreparedMarketState Helio
computed for it. This is the anti-hallucination / anti-contradiction gate:
schema-level errors (malformed JSON, out-of-range confidence) are handled by
pydantic before this ever runs (see schemas/thesis.py); this module handles
semantic checks that need to cross-reference the deterministic state.

NUMERIC_TOLERANCE_PCT absorbs LLM rounding/reformatting (e.g. "65432.1" vs
"65432.10") without letting a materially different number through — anything
outside this tolerance is treated as a possible hallucination and rejected.
"""
from __future__ import annotations

from helio.schemas.thesis import PreparedMarketState, Thesis, ThesisValidationResult

NUMERIC_TOLERANCE_PCT = 0.1


def _within_tolerance(actual: float, expected: float, tolerance_pct: float) -> bool:
    if expected == 0:
        return abs(actual) < 1e-9
    return abs(actual - expected) / abs(expected) * 100 <= tolerance_pct


def _reference_values(state: PreparedMarketState) -> dict[str, float]:
    return {
        "price": float(state.tf_15m.price),
        "ema20_4h": float(state.tf_4h.ema20),
        "ema50_4h": float(state.tf_4h.ema50),
        "ema200_4h": float(state.tf_4h.ema200),
        "atr_1h": float(state.tf_1h.atr),
        "volume_ratio": float(state.tf_1h.volume_ratio),
        "swing_high_1h": float(state.tf_1h.swing_high),
        "swing_low_1h": float(state.tf_1h.swing_low),
    }


def validate(thesis: Thesis, prepared_state: PreparedMarketState) -> ThesisValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if thesis.symbol != prepared_state.symbol:
        errors.append(f"thesis.symbol {thesis.symbol!r} does not match prepared state symbol {prepared_state.symbol!r}")

    if thesis.regime != prepared_state.regime:
        errors.append(f"thesis.regime {thesis.regime!r} does not match Helio-computed regime {prepared_state.regime!r}")

    if thesis.action == "BUY":
        if prepared_state.regime in ("BEAR_TREND", "HIGH_VOLATILITY_UNCLEAR"):
            errors.append(f"action BUY contradicts deterministic regime {prepared_state.regime}")

        if thesis.invalidation is None or not thesis.invalidation.condition.strip():
            errors.append("action BUY requires a non-empty invalidation.condition")

        failed_hard_gates = [e.name for e in prepared_state.evidence if e.hard_gate and not e.passed]
        if failed_hard_gates:
            errors.append(
                "action BUY is not supported by the evidence: failed hard-gate checks: "
                + ", ".join(failed_hard_gates)
            )
    # action == WAIT: no invalidation/evidence gating — WAIT is always a valid no-op verdict.

    reference = _reference_values(prepared_state)
    for field_name, expected in reference.items():
        actual_str = getattr(thesis.market_state, field_name)
        if actual_str is None:
            errors.append(f"market_state.{field_name} is missing — must be copied from the prepared market state")
            continue
        try:
            actual = float(actual_str)
        except ValueError:
            errors.append(f"market_state.{field_name}={actual_str!r} is not a valid number")
            continue
        if not _within_tolerance(actual, expected, NUMERIC_TOLERANCE_PCT):
            errors.append(
                f"market_state.{field_name}={actual_str!r} does not match Helio-computed "
                f"{expected!r} (tolerance {NUMERIC_TOLERANCE_PCT}%) — possible hallucination"
            )

    return ThesisValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
