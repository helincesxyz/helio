from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from helio.config import HelioSettings
from helio.conversation.store import ConversationStore
from helio.learning.store import EventStore
from helio.risk.config_loader import load_risk_config
from helio.risk.engine import RiskEngine
from helio.service.app import app
from helio.service.deps import AppState, reset_app_state_for_tests

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    risk_config = load_risk_config(FIXTURES_DIR / "sample_risk_config.yaml")
    state = AppState(
        settings=HelioSettings(mode="simulation"),
        risk_engine=RiskEngine(risk_config),
        event_store=EventStore(tmp_path / "events.sqlite3"),
        conversation_store=ConversationStore(tmp_path / "events.sqlite3"),
    )
    reset_app_state_for_tests(state)
    return TestClient(app)


def test_create_request_classifies_intent_and_persists_pending(client: TestClient):
    resp = client.post("/conversation/requests", json={"message": "Get me into BTC"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "GET_INTO_BTC"
    assert body["status"] == "PENDING"
    assert body["risk_profile"] == "balanced"
    assert body["response"] is None


def test_create_request_honors_explicit_risk_profile_and_conversation_id(client: TestClient):
    resp = client.post(
        "/conversation/requests",
        json={"message": "optimize my APY", "conversation_id": "conv-1", "risk_profile": "low"},
    )
    body = resp.json()
    assert body["conversation_id"] == "conv-1"
    assert body["risk_profile"] == "low"
    assert body["intent"] == "OPTIMIZE_APY"


def test_list_pending_returns_only_pending(client: TestClient):
    created = client.post("/conversation/requests", json={"message": "get into btc"}).json()
    client.post(
        f"/conversation/requests/{created['request_id']}/respond",
        json={"kind": "thesis", "thesis_id": "d1"},
    )
    client.post("/conversation/requests", json={"message": "optimize my money"})

    pending = client.get("/conversation/requests", params={"status": "pending"})
    assert pending.status_code == 200
    assert len(pending.json()) == 1
    assert pending.json()[0]["intent"] == "OPTIMIZE_MONEY"


def test_list_requires_pending_status_param(client: TestClient):
    resp = client.get("/conversation/requests")
    assert resp.status_code == 400


def test_get_by_id_404_when_missing(client: TestClient):
    resp = client.get("/conversation/requests/does-not-exist")
    assert resp.status_code == 404


def test_respond_answers_and_is_visible_on_get(client: TestClient):
    created = client.post("/conversation/requests", json={"message": "get into btc"}).json()
    respond = client.post(
        f"/conversation/requests/{created['request_id']}/respond",
        json={"kind": "thesis", "thesis_id": "decision-123"},
    )
    assert respond.status_code == 200
    assert respond.json()["status"] == "ANSWERED"
    assert respond.json()["response"]["thesis_id"] == "decision-123"

    fetched = client.get(f"/conversation/requests/{created['request_id']}")
    assert fetched.json()["status"] == "ANSWERED"


def test_respond_with_error_kind_marks_failed(client: TestClient):
    created = client.post("/conversation/requests", json={"message": "get into btc"}).json()
    respond = client.post(
        f"/conversation/requests/{created['request_id']}/respond",
        json={"kind": "error", "message": "MCP call failed"},
    )
    assert respond.json()["status"] == "FAILED"


def test_respond_twice_is_rejected(client: TestClient):
    created = client.post("/conversation/requests", json={"message": "get into btc"}).json()
    client.post(
        f"/conversation/requests/{created['request_id']}/respond",
        json={"kind": "unavailable", "message": "no workflow"},
    )
    second = client.post(
        f"/conversation/requests/{created['request_id']}/respond",
        json={"kind": "thesis", "thesis_id": "decision-999"},
    )
    assert second.status_code == 409


def test_respond_to_unknown_request_is_404(client: TestClient):
    resp = client.post(
        "/conversation/requests/does-not-exist/respond",
        json={"kind": "unavailable", "message": "n/a"},
    )
    assert resp.status_code == 404


def test_unknown_intent_round_trip(client: TestClient):
    created = client.post("/conversation/requests", json={"message": "what's the weather"}).json()
    assert created["intent"] == "UNKNOWN"
    respond = client.post(
        f"/conversation/requests/{created['request_id']}/respond",
        json={"kind": "unavailable", "message": "Helio doesn't have a workflow for that yet."},
    )
    assert respond.json()["status"] == "ANSWERED"
