from __future__ import annotations

from helio.strategy.base import Strategy
from helio.strategy.examples.sma_crossover import SmaCrossoverStrategy

STRATEGIES: dict[str, type[Strategy]] = {
    SmaCrossoverStrategy.name: SmaCrossoverStrategy,
}


def get_strategy(name: str) -> Strategy:
    try:
        return STRATEGIES[name]()
    except KeyError as exc:
        raise ValueError(f"unknown strategy {name!r}; available: {sorted(STRATEGIES)}") from exc
