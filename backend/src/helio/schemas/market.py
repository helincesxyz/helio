from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Candle(BaseModel):
    model_config = {"extra": "forbid"}

    ts: datetime
    o: str
    h: str
    l: str
    c: str
    vol: str


class MarketSnapshot(BaseModel):
    """Reshaped, non-secret market data, POSTed by Claude Code after calling
    market_get_ticker / market_get_candles via MCP."""

    model_config = {"extra": "forbid"}

    instId: str
    as_of: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_price: str
    candles: list[Candle] = Field(default_factory=list)
