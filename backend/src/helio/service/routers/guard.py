from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from helio.guard.config import GuardConfig
from helio.guard.context import GuardContext
from helio.schemas.account import AccountState
from helio.schemas.guard import GuardDecision, GuardRecord, GuardTradeIntent
from helio.service.deps import AppState, get_app_state

router = APIRouter(prefix="/guard", tags=["guard"])


@router.get("/config", response_model=GuardConfig)
def get_config(state: AppState = Depends(get_app_state)) -> GuardConfig:
    """Read-only view of the default ("balanced") GATE 3 policy (never
    contains credentials). See GET /guard/profiles for all three
    real, backend-enforced risk-preference tiers."""
    return state.guard_profiles["balanced"]


@router.get("/profiles", response_model=dict[str, GuardConfig])
def get_profiles(state: AppState = Depends(get_app_state)) -> dict[str, GuardConfig]:
    """The three real, immutable risk-preference profiles Gate 3 actually
    enforces — not a client-side scaling preview. Whichever tier a request
    selects (GuardTradeIntent.risk_profile / ConversationRequestIn.risk_profile)
    is the exact policy /guard/evaluate applies."""
    return state.guard_profiles


@router.post("/evaluate", response_model=GuardDecision)
def evaluate(
    intent: GuardTradeIntent, account: AccountState, state: AppState = Depends(get_app_state)
) -> GuardDecision:
    thesis_record = state.thesis_store.get_by_id(intent.thesis_id)
    is_duplicate = state.guard_store.exists_for_thesis(intent.thesis_id)

    ctx = GuardContext(account=account, thesis_record=thesis_record, is_duplicate=is_duplicate)
    engine = state.get_guard_engine(intent.risk_profile)
    decision = engine.evaluate(intent, ctx)
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
