from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

Intent = Literal["GET_INTO_BTC", "OPTIMIZE_MONEY", "OPTIMIZE_APY", "UNKNOWN"]
ConversationStatus = Literal["PENDING", "ANSWERED", "FAILED"]
RiskProfile = Literal["low", "balanced", "high"]
ResponseKind = Literal["thesis", "allocation_comparison", "apy_comparison", "unavailable", "error"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ConversationRequestIn(BaseModel):
    """What the frontend posts the instant a user hits send. `extra="forbid"`
    rejects any unexpected field at the boundary, same as every other
    Helio-facing schema."""

    model_config = {"extra": "forbid"}

    message: str = Field(min_length=1)
    conversation_id: str | None = None
    risk_profile: RiskProfile = "balanced"


class ConversationResponse(BaseModel):
    """Posted by whoever fulfills the request (Claude Code, per
    docs/runbooks/conversation_fulfillment.md) via
    POST /conversation/requests/{id}/respond — the only way an answer
    gets attached. Every field here must trace to a real MCP/computed
    value; never invented."""

    model_config = {"extra": "forbid"}

    kind: ResponseKind
    thesis_id: str | None = None
    comparison: dict | None = None
    message: str | None = None
    answered_at: datetime = Field(default_factory=_now)


class ConversationRequest(BaseModel):
    model_config = {"extra": "forbid"}

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str
    intent: Intent
    risk_profile: RiskProfile
    status: ConversationStatus = "PENDING"
    created_at: datetime = Field(default_factory=_now)
    response: ConversationResponse | None = None
