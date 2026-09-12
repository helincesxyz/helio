from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from helio.schemas.thesis import Invalidation, Target


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GuardTradeIntent(BaseModel):
    """A normalized, structured trade proposal derived from an approved
    (action="BUY") Thesis. This is the ONLY thing that may ever reach the
    GuardEngine — it carries no credentials and cannot, by itself, reach
    OKX; it must be APPROVEd first. `extra="forbid"` rejects any unexpected
    (e.g. credential-shaped) field at the boundary."""

    model_config = {"extra": "forbid"}

    trade_intent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit", "post_only", "fok", "ioc"]
    instrument_type: Literal["SPOT", "SWAP", "FUTURES", "OPTION", "MARGIN"] = "SPOT"
    leverage: str | None = None
    requested_notional: str
    requested_quantity: str
    entry_price: str
    invalidation: Invalidation | None = None
    target: Target | None = None
    strategy: str
    strategy_version: str
    thesis_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=_now)
    risk_profile: Literal["low", "balanced", "high"] = "balanced"


class GuardCheck(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    status: Literal["PASS", "FAIL"]
    reason: str


class GuardRiskSummary(BaseModel):
    model_config = {"extra": "forbid"}

    requested_notional: float
    max_allowed_notional: float
    estimated_loss: float | None = None
    risk_reward: float | None = None


class GuardDecision(BaseModel):
    model_config = {"extra": "forbid"}

    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    decision: Literal["APPROVE", "REJECT"]
    trade_intent_id: str
    checks: list[GuardCheck]
    risk_summary: GuardRiskSummary
    rejection_reasons: list[str] = Field(default_factory=list)
    policy_version: str
    evaluated_at: datetime = Field(default_factory=_now)


class GuardRecord(BaseModel):
    """What GET /guard/history and /guard/latest return."""

    model_config = {"extra": "forbid"}

    trade_intent_id: str
    logged_at: datetime
    trade_intent: GuardTradeIntent
    decision: GuardDecision
