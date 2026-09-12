from __future__ import annotations

from fastapi import APIRouter, Depends

from helio import __version__
from helio.service.deps import AppState, get_app_state

router = APIRouter(tags=["status"])


@router.get("/status")
def get_status(state: AppState = Depends(get_app_state)) -> dict[str, object]:
    return {
        "service": "helio",
        "version": __version__,
        "mode": state.settings.mode,
        "allow_live": state.risk_engine.config.allow_live,
    }
