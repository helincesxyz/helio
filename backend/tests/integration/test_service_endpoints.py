from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from helio.config import HelioSettings
from helio.learning.store import EventStore
from helio.risk.config_loader import load_risk_config
from helio.risk.engine import RiskEngine
from helio.service.app import app
from helio.service.deps import AppState, reset_app_state_for_tests
from helio.thesis.store import ThesisStore

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    risk_config = load_risk_config(FIXTURES_DIR / "sample_risk_config.yaml")
    state = AppState(
        settings=HelioSettings(mode="simulation"),
        risk_engine=RiskEngine(risk_config),
        event_store=EventStore(tmp_path / "events.sqlite3"),
        thesis_store=ThesisStore(tmp_path / "events.sqlite3"),
    )
    reset_app_state_for_tests(state)
    return TestClient(app)


def _intent_payload(**overrides) -> dict:
    payload = dict(
        strategy_id="test",
        symbol="BTC-USDT",
        instrument_type="SPOT",
        side="buy",
        order_type="market",
        size="10",
        size_unit="quote_ccy",
        rationale="integration test",
        mode="simulation",
        source="manual",
    )
    payload.update(overrides)
    return payload


def _account_payload(**overrides) -> dict:
    payload = dict(mode="simulation", balances=[{"ccy": "USDT", "avail": "1000", "total": "1000"}], positions=[])
    payload.update(overrides)
    return payload


def test_risk_evaluate_approves_valid_intent(client: TestClient):
    resp = client.post("/risk/evaluate", json={"intent": _intent_payload(), "account": _account_payload()})
    assert resp.status_code == 200
    assert resp.json()["approved"] is True


def test_risk_evaluate_rejects_live_intent(client: TestClient):
    resp = client.post(
        "/risk/evaluate", json={"intent": _intent_payload(mode="live"), "account": _account_payload()}
    )
    assert resp.status_code == 200
    assert resp.json()["approved"] is False
    assert "sim_vs_live_gate" in resp.json()["violated_rules"]


def test_risk_evaluate_rejects_credential_shaped_field(client: TestClient):
    intent = _intent_payload()
    intent["api_key"] = "leaked"
    resp = client.post("/risk/evaluate", json={"intent": intent, "account": _account_payload()})
    assert resp.status_code == 422


def test_learning_history_reflects_evaluated_intents(client: TestClient):
    client.post("/risk/evaluate", json={"intent": _intent_payload(), "account": _account_payload()})
    resp = client.get("/learning/history")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_strategy_signal_returns_list(client: TestClient):
    market = {"instId": "BTC-USDT", "last_price": "100", "candles": []}
    resp = client.post(
        "/strategy/signal",
        json={"strategy_id": "sma_crossover_v1", "market": market, "account": _account_payload(), "params": {}},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_strategy_signal_unknown_strategy_is_400(client: TestClient):
    market = {"instId": "BTC-USDT", "last_price": "100", "candles": []}
    resp = client.post(
        "/strategy/signal",
        json={"strategy_id": "does_not_exist", "market": market, "account": _account_payload(), "params": {}},
    )
    assert resp.status_code == 400


def test_state_account_round_trip(client: TestClient):
    client.post("/state/account", json=_account_payload())
    resp = client.get("/state/account")
    assert resp.status_code == 200
    assert resp.json()["mode"] == "simulation"


def test_verify_endpoint_reports_local_checks(client: TestClient):
    resp = client.get("/verify")
    assert resp.status_code == 200
    checks = {row["check"]: row["status"] for row in resp.json()}
    assert checks["RISK ENGINE"] == "PASS"
    assert checks["LEARNING ENGINE"] == "PASS"
    assert checks["OKX CONNECTION"] == "NOT RUN"


def test_verify_report_then_get_merges_mcp_rows(client: TestClient):
    client.post("/verify/report", json={"check": "OKX CONNECTION", "status": "PASS", "detail": "hasAuth: true"})
    resp = client.get("/verify")
    checks = {row["check"]: row["status"] for row in resp.json()}
    assert checks["OKX CONNECTION"] == "PASS"


def test_status_endpoint(client: TestClient):
    resp = client.get("/status")
    assert resp.status_code == 200
    assert resp.json()["mode"] == "simulation"
