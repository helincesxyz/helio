from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from helio.schemas.thesis import CandleBundle, PreparedMarketState, Thesis, ThesisRecord, ThesisValidationResult
from helio.service.deps import AppState, get_app_state
from helio.thesis.decision_quality import validate as validate_thesis
from helio.thesis.indicators import InsufficientDataError, InvalidIndicatorError
from helio.thesis.prepare import prepare_market_state

router = APIRouter(prefix="/thesis", tags=["thesis"])


@router.post("/prepare", response_model=PreparedMarketState)
def prepare(bundle: CandleBundle, state: AppState = Depends(get_app_state)) -> PreparedMarketState:
    try:
        prepared = prepare_market_state(bundle)
    except (InsufficientDataError, InvalidIndicatorError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    state.latest_thesis_state[bundle.symbol] = prepared
    return prepared


@router.post("/submit")
def submit(thesis: Thesis, state: AppState = Depends(get_app_state)) -> dict[str, object]:
    prepared_state = state.latest_thesis_state.get(thesis.symbol)
    if prepared_state is None:
        raise HTTPException(
            status_code=422,
            detail=f"no prepared market state for {thesis.symbol!r} — call /thesis/prepare first",
        )
    validation: ThesisValidationResult = validate_thesis(thesis, prepared_state)
    state.thesis_store.log(thesis, prepared_state, validation)
    return {"thesis": thesis.model_dump(mode="json"), "validation": validation.model_dump(mode="json")}


@router.get("/latest", response_model=ThesisRecord)
def latest(symbol: str, state: AppState = Depends(get_app_state)) -> ThesisRecord:
    record = state.thesis_store.get_latest(symbol)
    if record is None:
        raise HTTPException(status_code=404, detail=f"no thesis logged yet for {symbol!r}")
    return record


@router.get("/history", response_model=list[ThesisRecord])
def history(
    symbol: str | None = None, limit: int = 50, state: AppState = Depends(get_app_state)
) -> list[ThesisRecord]:
    if symbol:
        return state.thesis_store.get_by_symbol(symbol, limit=limit)
    return state.thesis_store.get_recent(limit=limit)
