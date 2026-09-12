from __future__ import annotations

from helio.learning.adjuster import ParameterAdjuster


def test_adjuster_always_returns_none_in_v1():
    adjuster = ParameterAdjuster()
    assert adjuster.suggest_adjustments("sma_crossover_v1", history=[]) is None
