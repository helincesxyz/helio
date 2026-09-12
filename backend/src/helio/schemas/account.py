from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class Balance(BaseModel):
    model_config = {"extra": "forbid"}

    ccy: str
    avail: str
    total: str


class Position(BaseModel):
    model_config = {"extra": "forbid"}

    instId: str
    posSide: str
    pos: str
    avgPx: str
    upl: str
    lever: str | None = None


class AccountState(BaseModel):
    """Reshaped, non-secret snapshot of OKX account state, POSTed by Claude
    Code after calling account_get_balance / account_get_positions via MCP."""

    model_config = {"extra": "forbid"}

    as_of: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mode: Literal["simulation", "live"]
    balances: list[Balance] = Field(default_factory=list)
    positions: list[Position] = Field(default_factory=list)
    open_orders_count: int = 0
    daily_realized_pnl_usd: str | None = None
