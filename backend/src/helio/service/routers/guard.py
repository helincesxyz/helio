from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from helio.guard.context import GuardContext
from helio.schemas.account import AccountState
from helio.schemas.guard import GuardDecision, GuardRecord, GuardTradeIntent
from helio.service.deps import AppState, get_app_state

router = APIRouter(prefix="/guard", tags=["guard"])


@router.post("/evaluate", response_model=GuardDecision)
def evaluate(
    intent: GuardTradeIntent, account: AccountState, state: AppState = Depends(get_app_state)
) -> GuardDecision:
    thesis_record = state.thesis_store.get_by_id(intent.thesis_id)
    is_duplicate = state.guard_store.exists_for_thesis(intent.thesis_id)

    ctx = GuardContext(account=account, thesis_record=thesis_record, is_duplicate=is_duplicate)
    decision = state.guard_engine.evaluate(intent, ctx)
    state.guard_store.log(intent, decision)
    return decision


@router.get("/latest", response_model=GuardRecord)
def latest(symbol: str, state: AppState = Depends(get_app_state)) -> GuardRecord:
    record = state.guard_store.get_latest(symbol)
    if record is None:
        raise HTTPException(status_code=404, detail=f"no guard decision logged yet for {symbol!r}")
    return record


@router.get("/history", response_model=list[GuardRecord])
def history(
    symbol: str | None = None, limit: int = 50, state: AppState = Depends(get_app_state)
) -> list[GuardRecord]:
    if symbol:
        return state.guard_store.get_by_symbol(symbol, limit=limit)
    return state.guard_store.get_recent(limit=limit)


@router.get("/for-thesis/{thesis_id}", response_model=GuardRecord)
def for_thesis(thesis_id: str, state: AppState = Depends(get_app_state)) -> GuardRecord:
    record = state.guard_store.get_by_thesis_id(thesis_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"no guard decision logged yet for thesis_id {thesis_id!r}")
    return record
