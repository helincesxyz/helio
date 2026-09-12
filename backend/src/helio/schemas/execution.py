from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from helio.schemas.account import AccountState

# "readonly" exercises authorize/prepare without ever intending a submission
# (used for kill-switch/expiry/rejection tests). "simulation" submits real
# MCP calls with simulatedTrading=true. "live" is real money — gated by the
# kill switch (helio.execution.kill_switch) and, even when the switch is on,
# Claude Code never calls the live order-placement tool itself; see
# docs/EXECUTION_PROTOCOL.md.
ExecutionMode = Literal["readonly", "simulation", "live"]

ExecutionStatus = Literal["SUBMITTED", "LIVE", "PARTIALLY_FILLED", "FILLED", "REJECTED", "UNKNOWN"]

# "execution_test" is every execution produced through this manual,
# human-initiated Gate 4 flow today — including the one real live BTC-USDT
# test buy. "autonomous_strategy" is reserved for a future unattended
# trading loop (Gate 5+) that does not exist yet; nothing in this codebase
# ever sets it.
ExecutionOrigin = Literal["execution_test", "autonomous_strategy"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionAuthorizeRequest(BaseModel):
    model_config = {"extra": "forbid"}

    trade_intent_id: str
    origin: ExecutionOrigin = "execution_test"


class ExecutionAuthorization(BaseModel):
    """Exact-intent-bound, single-use, short-lived authorization to attempt
    execution of one already-APPROVEd GuardDecision. `intent_hash` is a
    sha256 of the exact approved GuardTradeIntent this was issued for, so
    anyone auditing the flow can confirm nothing about the approved intent
    was altered between evaluation and execution."""

    model_config = {"extra": "forbid"}

    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trade_intent_id: str
    thesis_id: str
    risk_evaluation_id: str
    intent_hash: str
    authorized_at: datetime = Field(default_factory=_now)
    expires_at: datetime
    consumed: bool = False


class ExecutionPrepareRequest(BaseModel):
    model_config = {"extra": "forbid"}

    execution_id: str
    mode: ExecutionMode


class ExecutionPreparation(BaseModel):
    """The exact MCP call parameters for the authorized intent — what
    Claude Code (simulation) or the account owner (live) actually submits.
    Contains no credentials; only order-shape fields already public in the
    approved GuardTradeIntent."""

    model_config = {"extra": "forbid"}

    execution_id: str
    mode: ExecutionMode
    instId: str
    tdMode: Literal["cash"] = "cash"
    side: Literal["buy", "sell"]
    ordType: str
    sz: str
    simulatedTrading: bool
    prepared_at: datetime = Field(default_factory=_now)


class OrderState(BaseModel):
    """Reshaped OKX order state (mirrors the AccountState reshaping
    pattern — Claude Code posts this after calling spot_get_order /
    equivalent via MCP, never a raw passthrough)."""

    model_config = {"extra": "forbid"}

    okx_order_id: str
    state: Literal["live", "partially_filled", "filled", "canceled", "unknown"]
    filled_quantity: str = "0"
    avg_fill_price: str | None = None
    fee: str | None = None


class ExecutionSubmissionIn(BaseModel):
    """Posted to /execution/record-submission — the parsed OKX order
    placement response for the order actually submitted under this
    authorization."""

    model_config = {"extra": "forbid"}

    execution_id: str
    okx_order_id: str | None = None
    okx_code: str
    okx_scode: str | None = None
    okx_message: str | None = None


class ExecutionVerifyRequest(BaseModel):
    model_config = {"extra": "forbid"}

    execution_id: str
    order_state: OrderState
    account_state_before: AccountState | None = None
    account_state_after: AccountState


class ExecutionResult(BaseModel):
    model_config = {"extra": "forbid"}

    execution_id: str
    okx_order_id: str | None = None
    status: ExecutionStatus
    requested_quantity: str
    filled_quantity: str | None = None
    avg_fill_price: str | None = None
    fee: str | None = None
    mode: ExecutionMode
    origin: ExecutionOrigin


class ExecutionLifecycle(BaseModel):
    """The one row the Trades page and the final Gate 4 report read from —
    every ID and stage timestamp for one execution attempt, start to
    finish. `status` is None until a submission has been recorded;
    UNKNOWN is a terminal status once set — nothing in this codebase
    re-authorizes or retries from it."""

    model_config = {"extra": "forbid"}

    execution_id: str
    trade_intent_id: str
    thesis_id: str
    risk_evaluation_id: str
    intent_hash: str
    origin: ExecutionOrigin

    mode: ExecutionMode | None = None
    status: ExecutionStatus | None = None
    okx_order_id: str | None = None

    requested_quantity: str
    filled_quantity: str | None = None
    avg_fill_price: str | None = None
    fee: str | None = None

    expires_at: datetime
    consumed: bool = False

    authorized_at: datetime
    prepared_at: datetime | None = None
    submitted_at: datetime | None = None
    verified_at: datetime | None = None

    account_state_before: AccountState | None = None
    account_state_after: AccountState | None = None
