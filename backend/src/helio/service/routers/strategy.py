from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from helio.schemas.account import AccountState
from helio.schemas.market import MarketSnapshot
from helio.schemas.trade_intent import TradeIntent
from helio.service.deps import AppState, get_app_state
from helio.strategy.registry import get_strategy

router = APIRouter(prefix="/strategy", tags=["strategy"])


class StrategySignalRequest(BaseModel):
    model_config = {"extra": "forbid"}

    strategy_id: str
    market: MarketSnapshot
    account: AccountState
    params: dict[str, Any] = Field(default_factory=dict)


@router.post("/signal", response_model=list[TradeIntent])
def signal(req: StrategySignalRequest, state: AppState = Depends(get_app_state)) -> list[TradeIntent]:
    try:
        strategy = get_strategy(req.strategy_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    state.latest_market[req.market.instId] = req.market
    return strategy.generate_intents(req.market, req.account, req.params)
