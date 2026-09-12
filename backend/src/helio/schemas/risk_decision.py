from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class RuleResult(BaseModel):
    model_config = {"extra": "forbid"}

    rule: str
    passed: bool
    reason: str


class RiskDecision(BaseModel):
    """The deterministic verdict on a TradeIntent. Approval is required before
    Claude Code may call any OKX order-placement MCP tool for this intent."""

    model_config = {"extra": "forbid"}

    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    intent_id: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved: bool
    reasons: list[str] = Field(default_factory=list)
    violated_rules: list[str] = Field(default_factory=list)
    risk_config_hash: str
    computed: dict[str, str] = Field(default_factory=dict)
