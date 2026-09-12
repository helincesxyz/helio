from __future__ import annotations

import pytest

from helio.strategy.base import Strategy
from helio.strategy.registry import get_strategy


def test_strategy_is_abstract():
    with pytest.raises(TypeError):
        Strategy()  # type: ignore[abstract]


def test_registry_returns_known_strategy():
    strategy = get_strategy("sma_crossover_v1")
    assert strategy.name == "sma_crossover_v1"


def test_registry_raises_on_unknown_strategy():
    with pytest.raises(ValueError):
        get_strategy("does_not_exist")
