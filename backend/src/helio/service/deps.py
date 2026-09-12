from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from helio.config import HelioSettings, get_settings
from helio.conversation.store import ConversationStore
from helio.execution.gateway import ExecutionGateway
from helio.execution.store import ExecutionStore
from helio.learning.store import EventStore
from helio.logging_utils import configure_logging
from helio.risk.config_loader import load_risk_config
from helio.risk.engine import RiskEngine
from helio.guard.config import GuardConfig, load_guard_profiles
from helio.guard.engine import GuardEngine
from helio.guard.store import GuardStore
from helio.schemas.account import AccountState
from helio.schemas.market import MarketSnapshot
from helio.schemas.thesis import PreparedMarketState
from helio.thesis.store import ThesisStore


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
    latest_thesis_state: dict[str, PreparedMarketState] = field(default_factory=dict)
    thesis_store: ThesisStore | None = None
    # Immutable, loaded once at startup — never mutated per-request. A
    # fresh, stateless GuardEngine is constructed per call via
    # get_guard_engine(), so "per-request risk profile" never means shared
    # mutable state.
    guard_profiles: dict[str, GuardConfig] = field(default_factory=dict)
    guard_store: GuardStore | None = None
    conversation_store: ConversationStore | None = None
    execution_gateway: ExecutionGateway | None = None

    def get_guard_engine(self, profile: str) -> GuardEngine:
        config = self.guard_profiles.get(profile)
        if config is None:
            raise KeyError(f"unknown risk profile {profile!r}")
        return GuardEngine(config)


_state: AppState | None = None


def build_app_state() -> AppState:
    settings = get_settings()
    configure_logging(settings.log_level)
    risk_config = load_risk_config(settings.risk_config_path)
    guard_profiles = load_guard_profiles(settings.guard_config_path.parent)
    guard_store = GuardStore(settings.db_path)
    return AppState(
        settings=settings,
        risk_engine=RiskEngine(risk_config),
        event_store=EventStore(settings.db_path),
        thesis_store=ThesisStore(settings.db_path),
        guard_profiles=guard_profiles,
        guard_store=guard_store,
        conversation_store=ConversationStore(settings.db_path),
        execution_gateway=ExecutionGateway(ExecutionStore(settings.db_path), guard_store),
    )


def get_app_state() -> AppState:
    global _state
    if _state is None:
        _state = build_app_state()
    return _state


def reset_app_state_for_tests(state: AppState) -> None:
    global _state
    _state = state
