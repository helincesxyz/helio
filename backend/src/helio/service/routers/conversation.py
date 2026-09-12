from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from helio.conversation.intent import classify_intent
from helio.schemas.conversation import ConversationRequest, ConversationRequestIn, ConversationResponse
from helio.service.deps import AppState, get_app_state

router = APIRouter(prefix="/conversation", tags=["conversation"])


@router.post("/requests", response_model=ConversationRequest)
def create_request(
    payload: ConversationRequestIn, state: AppState = Depends(get_app_state)
) -> ConversationRequest:
    request_kwargs: dict[str, object] = {
        "message": payload.message,
        "intent": classify_intent(payload.message),
        "risk_profile": payload.risk_profile,
    }
    if payload.conversation_id:
        request_kwargs["conversation_id"] = payload.conversation_id
    request = ConversationRequest(**request_kwargs)
    state.conversation_store.create(request)
    return request


@router.get("/requests", response_model=list[ConversationRequest])
def list_requests(
    status: str | None = None, limit: int = 50, state: AppState = Depends(get_app_state)
) -> list[ConversationRequest]:
    if status != "pending":
        raise HTTPException(status_code=400, detail="only status=pending is supported")
    return state.conversation_store.get_pending(limit=limit)


@router.get("/requests/{request_id}", response_model=ConversationRequest)
def get_request(request_id: str, state: AppState = Depends(get_app_state)) -> ConversationRequest:
    record = state.conversation_store.get_by_id(request_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"no conversation request {request_id!r}")
    return record


@router.post("/requests/{request_id}/respond", response_model=ConversationRequest)
def respond(
    request_id: str, response: ConversationResponse, state: AppState = Depends(get_app_state)
) -> ConversationRequest:
    try:
        return state.conversation_store.respond(request_id, response)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
