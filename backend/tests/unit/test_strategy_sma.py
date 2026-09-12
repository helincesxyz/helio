from __future__ import annotations

from datetime import datetime, timedelta, timezone

from helio.schemas.account import AccountState
from helio.schemas.market import Candle, MarketSnapshot
from helio.strategy.examples.sma_crossover import SmaCrossoverStrategy


def _market(closes: list[float]) -> MarketSnapshot:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    candles = [
        Candle(ts=base + timedelta(minutes=i), o=str(c), h=str(c), l=str(c), c=str(c), vol="1")
        for i, c in enumerate(closes)
    ]
    return MarketSnapshot(instId="BTC-USDT", last_price=str(closes[-1]), candles=candles)


def _account() -> AccountState:
    return AccountState(mode="simulation")


def test_sma_crossover_emits_buy_on_upward_cross():
    strategy = SmaCrossoverStrategy()
    market = _market([10, 10, 10, 10, 20])
    intents = strategy.generate_intents(market, _account(), {"fast_period": 2, "slow_period": 4})
    assert len(intents) == 1
    assert intents[0].side == "buy"
    assert intents[0].strategy_id == "sma_crossover_v1"


def test_sma_crossover_emits_sell_on_downward_cross():
    strategy = SmaCrossoverStrategy()
    market = _market([20, 20, 20, 20, 10])
    intents = strategy.generate_intents(market, _account(), {"fast_period": 2, "slow_period": 4})
    assert len(intents) == 1
    assert intents[0].side == "sell"


def test_sma_crossover_emits_nothing_without_cross():
    strategy = SmaCrossoverStrategy()
    market = _market([10, 10, 10, 10, 10])
    intents = strategy.generate_intents(market, _account(), {"fast_period": 2, "slow_period": 4})
    assert intents == []


def test_sma_crossover_emits_nothing_with_insufficient_data():
    strategy = SmaCrossoverStrategy()
    market = _market([10, 20])
    intents = strategy.generate_intents(market, _account(), {"fast_period": 2, "slow_period": 4})
    assert intents == []
