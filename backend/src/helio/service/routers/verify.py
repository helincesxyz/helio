from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from helio.risk.checks import run_local_checks
from helio.service.deps import AppState, VerifyRow, get_app_state

router = APIRouter(prefix="/verify", tags=["verify"])

MCP_SOURCED_CHECKS = [
    "OKX CONNECTION",
    "ACCOUNT",
    "MARKET DATA",
    "PORTFOLIO",
    "SPOT EXECUTION",
]
STALE_AFTER = timedelta(minutes=15)


class VerifyReportRequest(BaseModel):
    model_config = {"extra": "forbid"}

    check: str
    status: str  # "PASS" | "FAIL"
    detail: str = ""


@router.post("/report")
def report(req: VerifyReportRequest, state: AppState = Depends(get_app_state)) -> dict[str, str]:
    state.verify_rows[req.check] = VerifyRow(
        check=req.check, status=req.status, detail=req.detail, reported_at=datetime.now(timezone.utc)
    )
    return {"status": "recorded"}


@router.get("")
def get_verify(state: AppState = Depends(get_app_state)) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for name, passed, detail in run_local_checks(state):
        rows.append({"check": name, "status": "PASS" if passed else "FAIL", "detail": detail})

    now = datetime.now(timezone.utc)
    for name in MCP_SOURCED_CHECKS:
        row = state.verify_rows.get(name)
        if row is None:
            rows.append({"check": name, "status": "NOT RUN", "detail": "no report received yet"})
        elif now - row.reported_at > STALE_AFTER:
            rows.append({"check": name, "status": "STALE", "detail": row.detail})
        else:
            rows.append({"check": name, "status": row.status, "detail": row.detail})

    return rows
