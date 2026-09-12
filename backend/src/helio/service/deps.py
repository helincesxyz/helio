from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from helio.config import HelioSettings, get_settings
from helio.learning.store import EventStore
from helio.logging_utils import configure_logging
from helio.risk.config_loader import load_risk_config
from helio.risk.engine import RiskEngine
from helio.schemas.account import AccountState
from helio.schemas.market import MarketSnapshot


@dataclass
class VerifyRow:
    check: str
    status: str  # "PASS" | "FAIL"
    detail: str
    reported_at: datetime


@dataclass
class AppState:
    settings: HelioSettings
    risk_engine: RiskEngine
    event_store: EventStore
    latest_account: AccountState | None = None
    latest_market: dict[str, MarketSnapshot] = field(default_factory=dict)
    verify_rows: dict[str, VerifyRow] = field(default_factory=dict)


_state: AppState | None = None


def build_app_state() -> AppState:
    settings = get_settings()
    configure_logging(settings.log_level)
    risk_config = load_risk_config(settings.risk_config_path)
    return AppState(
        settings=settings,
        risk_engine=RiskEngine(risk_config),
        event_store=EventStore(settings.db_path),
    )


def get_app_state() -> AppState:
    global _state
    if _state is None:
        _state = build_app_state()
    return _state


def reset_app_state_for_tests(state: AppState) -> None:
    global _state
    _state = state
