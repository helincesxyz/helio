from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from helio.config import HelioSettings
from helio.execution.gateway import ExecutionGateway
from helio.execution.store import ExecutionStore
from helio.guard.config import load_guard_config
from helio.guard.context import GuardContext
from helio.guard.engine import GuardEngine
from helio.guard.store import GuardStore
from helio.learning.store import EventStore
from helio.risk.config_loader import load_risk_config
from helio.risk.engine import RiskEngine
from helio.schemas.account import AccountState, Balance
from helio.schemas.guard import GuardTradeIntent, Invalidation, Target
from helio.schemas.thesis import EvidenceItem, PreparedMarketState, Thesis, ThesisMarketStateEcho, ThesisRecord, ThesisValidationResult, TimeframeIndicators
from helio.service.app import app
from helio.service.deps import AppState, reset_app_state_for_tests
from helio.thesis.store import ThesisStore

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _tf(timeframe: str) -> TimeframeIndicators:
    return TimeframeIndicators(
        timeframe=timeframe, candle_count=300, price="50000", ema20="49000", ema50="48000", ema200="47000",
        atr="500", atr_pct="1.0", volume="100", volume_avg="80", volume_ratio="1.5",
        swing_high="50500", swing_low="48500", price_change_pct="2.0",
    )


def _approved_intent(guard_store: GuardStore, guard_config, thesis_id="thesis-1") -> GuardTradeIntent:
    thesis = Thesis(
        decision_id=thesis_id, symbol="BTC-USDT", regime="BULL_TREND", action="BUY", confidence=0.75,
        thesis="test", evidence=["e"], market_state=ThesisMarketStateEcho(),
    )
    prepared = PreparedMarketState(
        symbol="BTC-USDT", tf_4h=_tf("4H"), tf_1h=_tf("1H"), tf_15m=_tf("15m"),
        regime="BULL_TREND", regime_reason="test", evidence=[EvidenceItem(name="x", passed=True, detail="", hard_gate=True)],
        candidate_action="BUY",
    )
    record = ThesisRecord(decision_id=thesis_id, logged_at="2024-01-01T00:00:00Z", thesis=thesis, prepared_state=prepared, validation=ThesisValidationResult(valid=True))

    intent = GuardTradeIntent(
        symbol="BTC-USDT", side="buy", order_type="market", requested_notional="50", requested_quantity="0.001",
        entry_price="50000", invalidation=Invalidation(condition="c", price="48500"), target=Target(price="53000"),
        strategy="trend_breakout", strategy_version="v1", thesis_id=thesis_id, confidence=0.75,
    )
    account = AccountState(mode="simulation", balances=[Balance(ccy="USDT", avail="1000", total="1000")], positions=[], daily_realized_pnl_usd="0")
    engine = GuardEngine(guard_config)
    ctx = GuardContext(account=account, thesis_record=record, is_duplicate=False)
    decision = engine.evaluate(intent, ctx)
    assert decision.decision == "APPROVE"
    guard_store.log(intent, decision)
    return intent


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("HELIO_LIVE_EXECUTION_ENABLED", raising=False)
    risk_config = load_risk_config(FIXTURES_DIR / "sample_risk_config.yaml")
    guard_config = load_guard_config(FIXTURES_DIR / "sample_guard_config.yaml")
    db_path = tmp_path / "events.sqlite3"
    guard_store = GuardStore(db_path)
    state = AppState(
        settings=HelioSettings(mode="simulation"),
        risk_engine=RiskEngine(risk_config),
        event_store=EventStore(db_path),
        thesis_store=ThesisStore(db_path),
        guard_profiles={"low": guard_config, "balanced": guard_config, "high": guard_config},
        guard_store=guard_store,
        execution_gateway=ExecutionGateway(ExecutionStore(db_path), guard_store),
    )
    reset_app_state_for_tests(state)
    test_client = TestClient(app)
    test_client._guard_store = guard_store  # type: ignore[attr-defined]
    test_client._guard_config = guard_config  # type: ignore[attr-defined]
    return test_client


def test_full_lifecycle_authorize_prepare_submit_verify(client: TestClient):
    intent = _approved_intent(client._guard_store, client._guard_config)

    auth = client.post("/execution/authorize", json={"trade_intent_id": intent.trade_intent_id})
    assert auth.status_code == 200
    execution_id = auth.json()["execution_id"]

    prep = client.post("/execution/prepare", json={"execution_id": execution_id, "mode": "simulation"})
    assert prep.status_code == 200
    assert prep.json()["simulatedTrading"] is True

    submit = client.post(
        "/execution/record-submission",
        json={"execution_id": execution_id, "okx_order_id": "okx-1", "okx_code": "0", "okx_scode": "0"},
    )
    assert submit.status_code == 200
    assert submit.json()["status"] == "SUBMITTED"

    verify = client.post(
        "/execution/verify",
        json={
            "execution_id": execution_id,
            "order_state": {"okx_order_id": "okx-1", "state": "filled", "filled_quantity": "0.001", "avg_fill_price": "50000"},
            "account_state_after": {"mode": "simulation", "balances": [{"ccy": "USDT", "avail": "950", "total": "950"}], "positions": []},
        },
    )
    assert verify.status_code == 200
    assert verify.json()["status"] == "FILLED"

    fetched = client.get(f"/execution/{execution_id}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "FILLED"


def test_authorize_unknown_intent_is_404(client: TestClient):
    resp = client.post("/execution/authorize", json={"trade_intent_id": "does-not-exist"})
    assert resp.status_code == 404


def test_authorize_rejected_intent_is_409(client: TestClient):
    thesis = Thesis(
        decision_id="thesis-rej", symbol="BTC-USDT", regime="RANGE", action="WAIT", confidence=0.5,
        thesis="test", evidence=["e"], market_state=ThesisMarketStateEcho(),
    )
    prepared = PreparedMarketState(
        symbol="BTC-USDT", tf_4h=_tf("4H"), tf_1h=_tf("1H"), tf_15m=_tf("15m"),
        regime="RANGE", regime_reason="test", evidence=[], candidate_action="WAIT",
    )
    record = ThesisRecord(decision_id="thesis-rej", logged_at="2024-01-01T00:00:00Z", thesis=thesis, prepared_state=prepared, validation=ThesisValidationResult(valid=True))
    intent = GuardTradeIntent(
        symbol="BTC-USDT", side="buy", order_type="market", requested_notional="50", requested_quantity="0.001",
        entry_price="50000", strategy="trend_breakout", strategy_version="v1", thesis_id="thesis-rej", confidence=0.5,
    )
    account = AccountState(mode="simulation", balances=[Balance(ccy="USDT", avail="1000", total="1000")], positions=[], daily_realized_pnl_usd="0")
    engine = GuardEngine(client._guard_config)
    ctx = GuardContext(account=account, thesis_record=record, is_duplicate=False)
    decision = engine.evaluate(intent, ctx)
    assert decision.decision == "REJECT"
    client._guard_store.log(intent, decision)

    resp = client.post("/execution/authorize", json={"trade_intent_id": intent.trade_intent_id})
    assert resp.status_code == 409


def test_prepare_live_blocked_by_kill_switch(client: TestClient):
    intent = _approved_intent(client._guard_store, client._guard_config, thesis_id="thesis-live")
    auth = client.post("/execution/authorize", json={"trade_intent_id": intent.trade_intent_id}).json()
    resp = client.post("/execution/prepare", json={"execution_id": auth["execution_id"], "mode": "live"})
    assert resp.status_code == 403


def test_duplicate_authorize_is_409(client: TestClient):
    intent = _approved_intent(client._guard_store, client._guard_config, thesis_id="thesis-dup")
    first = client.post("/execution/authorize", json={"trade_intent_id": intent.trade_intent_id})
    assert first.status_code == 200
    second = client.post("/execution/authorize", json={"trade_intent_id": intent.trade_intent_id})
    assert second.status_code == 409


def test_get_execution_404_when_missing(client: TestClient):
    resp = client.get("/execution/does-not-exist")
    assert resp.status_code == 404


def test_list_executions_by_thesis(client: TestClient):
    intent = _approved_intent(client._guard_store, client._guard_config, thesis_id="thesis-list")
    client.post("/execution/authorize", json={"trade_intent_id": intent.trade_intent_id})
    resp = client.get("/execution", params={"thesis_id": "thesis-list"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
