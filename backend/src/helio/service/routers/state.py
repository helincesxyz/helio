from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from helio.schemas.account import AccountState
from helio.schemas.market import MarketSnapshot
from helio.service.deps import AppState, get_app_state

router = APIRouter(prefix="/state", tags=["state"])


@router.post("/account")
def post_account(account: AccountState, state: AppState = Depends(get_app_state)) -> dict[str, str]:
    state.latest_account = account
    return {"status": "stored"}


@router.get("/account", response_model=AccountState)
def get_account(state: AppState = Depends(get_app_state)) -> AccountState:
    if state.latest_account is None:
        raise HTTPException(status_code=404, detail="no account state has been posted yet")
    return state.latest_account


@router.post("/market")
def post_market(market: MarketSnapshot, state: AppState = Depends(get_app_state)) -> dict[str, str]:
    state.latest_market[market.instId] = market
    return {"status": "stored"}


@router.get("/market", response_model=MarketSnapshot)
def get_market(instId: str, state: AppState = Depends(get_app_state)) -> MarketSnapshot:
    snapshot = state.latest_market.get(instId)
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"no market state posted yet for {instId}")
    return snapshot
