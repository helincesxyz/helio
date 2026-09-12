from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from helio.schemas.risk_decision import RiskDecision
from helio.schemas.trade_intent import TradeIntent


class ExecutionResult(BaseModel):
    """Sourced from the OKX order response Claude Code receives via MCP
    (e.g. spot_place_order) — contains no credentials, just order state."""

    model_config = {"extra": "forbid"}

    ord_id: str
    status: str
    avg_px: str | None = None
    fill_sz: str | None = None
    source: str = "mcp"


class Outcome(BaseModel):
    model_config = {"extra": "forbid"}

    realized_pnl_usd: str | None = None
    closed_at: datetime | None = None


class LearningEvent(BaseModel):
    model_config = {"extra": "forbid"}

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    intent: TradeIntent
    decision: RiskDecision
    execution_result: ExecutionResult | None = None
    outcome: Outcome | None = None
    logged_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
