from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from helio.execution.gateway import InvalidStateError, KillSwitchError, NotFoundError
from helio.schemas.execution import (
    ExecutionAuthorizeRequest,
    ExecutionAuthorization,
    ExecutionLifecycle,
    ExecutionPrepareRequest,
    ExecutionPreparation,
    ExecutionResult,
    ExecutionSubmissionIn,
    ExecutionVerifyRequest,
)
from helio.service.deps import AppState, get_app_state

router = APIRouter(prefix="/execution", tags=["execution"])


def _handle(fn):
    try:
        return fn()
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KillSwitchError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except InvalidStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/authorize", response_model=ExecutionAuthorization)
def authorize(
    payload: ExecutionAuthorizeRequest, state: AppState = Depends(get_app_state)
) -> ExecutionAuthorization:
    return _handle(lambda: state.execution_gateway.authorize(payload.trade_intent_id, payload.origin))


@router.post("/prepare", response_model=ExecutionPreparation)
def prepare(payload: ExecutionPrepareRequest, state: AppState = Depends(get_app_state)) -> ExecutionPreparation:
    return _handle(lambda: state.execution_gateway.prepare(payload.execution_id, payload.mode))


@router.post("/record-submission", response_model=ExecutionResult)
def record_submission(
    payload: ExecutionSubmissionIn, state: AppState = Depends(get_app_state)
) -> ExecutionResult:
    return _handle(lambda: state.execution_gateway.record_submission(payload))


@router.post("/verify", response_model=ExecutionLifecycle)
def verify(payload: ExecutionVerifyRequest, state: AppState = Depends(get_app_state)) -> ExecutionLifecycle:
    return _handle(lambda: state.execution_gateway.verify(payload))


@router.get("/{execution_id}", response_model=ExecutionLifecycle)
def get_execution(execution_id: str, state: AppState = Depends(get_app_state)) -> ExecutionLifecycle:
    lifecycle = state.execution_gateway.get(execution_id)
    if lifecycle is None:
        raise HTTPException(status_code=404, detail=f"no execution {execution_id!r}")
    return lifecycle


@router.get("", response_model=list[ExecutionLifecycle])
def list_executions(
    thesis_id: str | None = None, limit: int = 50, state: AppState = Depends(get_app_state)
) -> list[ExecutionLifecycle]:
    if thesis_id:
        return state.execution_gateway.get_by_thesis_id(thesis_id)
    return state.execution_gateway.get_recent(limit=limit)
