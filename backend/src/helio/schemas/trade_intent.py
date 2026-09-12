from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class TradeIntent(BaseModel):
    """A structured, non-executing proposal to trade — the only thing an LLM
    or strategy is allowed to produce. It carries no credentials and cannot,
    by itself, reach OKX; it must pass through RiskEngine.evaluate() first."""

    model_config = {"extra": "forbid"}

    intent_id: str = Field(default_factory=_new_id)
    created_at: datetime = Field(default_factory=_now)
    strategy_id: str
    symbol: str  # OKX instId, e.g. "BTC-USDT"
    instrument_type: Literal["SPOT", "SWAP", "FUTURES", "OPTION"]
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit", "post_only", "fok", "ioc"]
    size: str  # decimal-as-string — never a float, to avoid precision drift
    size_unit: Literal["base_ccy", "quote_ccy", "contracts"]
    price: str | None = None
    leverage: str | None = None
    rationale: str
    confidence: float | None = None
    mode: Literal["simulation", "live"]
    source: Literal["llm", "strategy", "manual"]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("size", "price", "leverage")
    @classmethod
    def _must_be_decimal_string(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            float(v)
        except ValueError as exc:
            raise ValueError(f"expected a decimal string, got {v!r}") from exc
        return v
