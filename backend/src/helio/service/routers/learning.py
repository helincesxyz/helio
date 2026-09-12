from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from helio.schemas.events import ExecutionResult, LearningEvent, Outcome
from helio.service.deps import AppState, get_app_state

router = APIRouter(prefix="/learning", tags=["learning"])


class LogExecutionRequest(BaseModel):
    model_config = {"extra": "forbid"}

    intent_id: str
    result: ExecutionResult


class LogOutcomeRequest(BaseModel):
    model_config = {"extra": "forbid"}

    intent_id: str
    outcome: Outcome


@router.post("/log/execution")
def log_execution(req: LogExecutionRequest, state: AppState = Depends(get_app_state)) -> dict[str, str]:
    state.event_store.log_execution(req.intent_id, req.result)
    return {"status": "logged"}


@router.post("/log/outcome")
def log_outcome(req: LogOutcomeRequest, state: AppState = Depends(get_app_state)) -> dict[str, str]:
    state.event_store.log_outcome(req.intent_id, req.outcome)
    return {"status": "logged"}


@router.get("/history", response_model=list[LearningEvent])
def history(
    limit: int = 50, strategy_id: str | None = None, state: AppState = Depends(get_app_state)
) -> list[LearningEvent]:
    if strategy_id:
        return state.event_store.get_by_strategy(strategy_id)
    return state.event_store.get_recent(limit)
