from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from helio.schemas.market import Candle

Timeframe = Literal["4H", "1H", "15m"]
RegimeLabel = Literal["BULL_TREND", "BEAR_TREND", "RANGE", "HIGH_VOLATILITY_UNCLEAR"]
ActionLabel = Literal["BUY", "WAIT"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TimeframeIndicators(BaseModel):
    model_config = {"extra": "forbid"}

    timeframe: Timeframe
    as_of: datetime = Field(default_factory=_now)
    candle_count: int
    price: str
    ema20: str
    ema50: str
    ema200: str
    atr: str
    atr_pct: str
    volume: str
    volume_avg: str
    volume_ratio: str
    swing_high: str
    swing_low: str
    price_change_pct: str


class EvidenceItem(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    passed: bool
    detail: str
    hard_gate: bool


class PreparedMarketState(BaseModel):
    """What Helio hands back to Claude Code after /thesis/prepare: every
    deterministic number and the evidence checklist, computed in Python.
    The LLM reads this — it never recomputes indicators from raw candles."""

    model_config = {"extra": "forbid"}

    symbol: str
    prepared_at: datetime = Field(default_factory=_now)
    tf_4h: TimeframeIndicators
    tf_1h: TimeframeIndicators
    tf_15m: TimeframeIndicators
    regime: RegimeLabel
    regime_reason: str
    evidence: list[EvidenceItem]
    candidate_action: ActionLabel
    strategy: Literal["trend_breakout"] = "trend_breakout"
    strategy_version: Literal["v1"] = "v1"


class Invalidation(BaseModel):
    model_config = {"extra": "forbid"}

    condition: str
    price: str | None = None


class Target(BaseModel):
    model_config = {"extra": "forbid"}

    price: str | None = None


class ThesisMarketStateEcho(BaseModel):
    """The numbers the LLM must copy verbatim from PreparedMarketState —
    never invent. Cross-checked by decision_quality.validate() against the
    Helio-computed PreparedMarketState it was given."""

    model_config = {"extra": "forbid"}

    price: str | None = None
    ema20_4h: str | None = None
    ema50_4h: str | None = None
    ema200_4h: str | None = None
    atr_1h: str | None = None
    volume_ratio: str | None = None  # 1H volume ratio
    swing_high_1h: str | None = None
    swing_low_1h: str | None = None


class Thesis(BaseModel):
    """Assembled by the LLM (Claude Code) from a PreparedMarketState and
    submitted via POST /thesis/submit. `extra="forbid"` rejects any
    unexpected (e.g. credential-shaped) field at the boundary."""

    model_config = {"extra": "forbid"}

    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    timestamp: datetime = Field(default_factory=_now)
    regime: RegimeLabel
    strategy: Literal["trend_breakout"] = "trend_breakout"
    strategy_version: Literal["v1"] = "v1"
    action: ActionLabel
    confidence: float = Field(ge=0.0, le=1.0)
    thesis: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    invalidation: Invalidation | None = None
    target: Target | None = None
    risk_reward: float | None = None
    market_state: ThesisMarketStateEcho


class ThesisValidationResult(BaseModel):
    model_config = {"extra": "forbid"}

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CandleBundle(BaseModel):
    """Input to POST /thesis/prepare — raw candles Claude Code fetched via
    market_get_candles (MCP), reshaped into Helio's Candle schema."""

    model_config = {"extra": "forbid"}

    symbol: str
    tf_4h: list[Candle]
    tf_1h: list[Candle]
    tf_15m: list[Candle]


class ThesisRecord(BaseModel):
    model_config = {"extra": "forbid"}

    decision_id: str
    logged_at: datetime
    thesis: Thesis
    prepared_state: PreparedMarketState
    validation: ThesisValidationResult
