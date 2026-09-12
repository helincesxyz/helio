from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from helio.risk.config_loader import RiskConfig
from helio.schemas.account import AccountState
from helio.schemas.risk_decision import RiskDecision
from helio.schemas.trade_intent import TradeIntent
from helio.service.deps import AppState, get_app_state

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/config", response_model=RiskConfig)
def get_config(state: AppState = Depends(get_app_state)) -> RiskConfig:
    """Read-only view of the active risk limits (never contains credentials)."""
    return state.risk_engine.config


class RiskEvaluateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    intent: TradeIntent
    account: AccountState


@router.post("/evaluate", response_model=RiskDecision)
def evaluate(req: RiskEvaluateRequest, state: AppState = Depends(get_app_state)) -> RiskDecision:
    state.event_store.log_intent(req.intent)
    decision = state.risk_engine.evaluate(req.intent, req.account)
    state.event_store.log_decision(decision)
    state.latest_account = req.account
    return decision
