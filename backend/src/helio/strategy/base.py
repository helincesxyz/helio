from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from helio.schemas.account import AccountState
from helio.schemas.market import MarketSnapshot
from helio.schemas.trade_intent import TradeIntent


class Strategy(ABC):
    """A pluggable signal generator. Strategies never touch OKX or risk
    limits directly — they only propose TradeIntents, which the RiskEngine
    must approve before Claude Code executes them via MCP."""

    name: str

    @abstractmethod
    def generate_intents(
        self, market: MarketSnapshot, account: AccountState, params: dict[str, Any]
    ) -> list[TradeIntent]:
        """Return zero or more TradeIntents given the latest market/account state."""
        raise NotImplementedError
