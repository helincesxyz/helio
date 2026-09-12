from __future__ import annotations

from typing import Any

from helio.schemas.account import AccountState
from helio.schemas.market import MarketSnapshot
from helio.schemas.trade_intent import TradeIntent
from helio.strategy.base import Strategy


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


class SmaCrossoverStrategy(Strategy):
    """A minimal example strategy: proposes a buy when the fast SMA crosses
    above the slow SMA, and a sell when it crosses below. No ML, no
    portfolio optimization — this exists to demonstrate the Strategy
    interface end-to-end, not to be profitable."""

    name = "sma_crossover_v1"

    def generate_intents(
        self, market: MarketSnapshot, account: AccountState, params: dict[str, Any]
    ) -> list[TradeIntent]:
        fast_period = int(params.get("fast_period", 10))
        slow_period = int(params.get("slow_period", 30))
        notional = str(params.get("order_notional_usd", 50))

        closes = [float(c.c) for c in market.candles]
        if len(closes) < slow_period + 1:
            return []

        fast_prev = _sma(closes[:-1], fast_period)
        slow_prev = _sma(closes[:-1], slow_period)
        fast_now = _sma(closes, fast_period)
        slow_now = _sma(closes, slow_period)
        if None in (fast_prev, slow_prev, fast_now, slow_now):
            return []

        crossed_up = fast_prev <= slow_prev and fast_now > slow_now
        crossed_down = fast_prev >= slow_prev and fast_now < slow_now

        if not (crossed_up or crossed_down):
            return []

        side = "buy" if crossed_up else "sell"
        return [
            TradeIntent(
                strategy_id=self.name,
                symbol=market.instId,
                instrument_type="SPOT",
                side=side,
                order_type="market",
                size=notional,
                size_unit="quote_ccy",
                rationale=(
                    f"fast SMA({fast_period})={fast_now:.2f} crossed "
                    f"{'above' if crossed_up else 'below'} slow SMA({slow_period})={slow_now:.2f}"
                ),
                mode=account.mode,
                source="strategy",
            )
        ]
