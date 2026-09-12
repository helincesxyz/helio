from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from helio.config import HelioSettings
from helio.guard.config import load_guard_config
from helio.guard.engine import GuardEngine
from helio.guard.store import GuardStore
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
    guard_config = load_guard_config(FIXTURES_DIR / "sample_guard_config.yaml")
    db_path = tmp_path / "events.sqlite3"
    state = AppState(
        settings=HelioSettings(mode="simulation"),
        risk_engine=RiskEngine(risk_config),
        event_store=EventStore(db_path),
        thesis_store=ThesisStore(db_path),
        guard_engine=GuardEngine(guard_config),
        guard_store=GuardStore(db_path),
    )
    reset_app_state_for_tests(state)
    return TestClient(app)


def _account_payload(**overrides):
    payload = dict(
        mode="simulation",
        balances=[{"ccy": "USDT", "avail": "1000", "total": "1000"}],
        positions=[],
        daily_realized_pnl_usd="0",
    )
    payload.update(overrides)
    return payload


def _log_thesis(client: TestClient, action="BUY", confidence=0.75) -> str:
    bundle_market = {
        "symbol": "BTC-USDT",
        "tf_4h": _synthetic_candles("up"),
        "tf_1h": _synthetic_candles("up", volume_spike_at=-1),
        "tf_15m": _synthetic_candles("up"),
    }
    prepared = client.post("/thesis/prepare", json=bundle_market).json()
    thesis = {
        "symbol": "BTC-USDT",
        "regime": prepared["regime"],
        "action": action,
        "confidence": confidence,
        "thesis": "integration test thesis",
        "evidence": [e["detail"] for e in prepared["evidence"]],
        "invalidation": (
            {"condition": "close below swing low", "price": prepared["tf_1h"]["swing_low"]}
            if action == "BUY"
            else None
        ),
        "target": {"price": str(float(prepared["tf_15m"]["price"]) * 1.05)} if action == "BUY" else None,
        "market_state": {
            "price": prepared["tf_15m"]["price"],
            "ema20_4h": prepared["tf_4h"]["ema20"],
            "ema50_4h": prepared["tf_4h"]["ema50"],
            "ema200_4h": prepared["tf_4h"]["ema200"],
            "atr_1h": prepared["tf_1h"]["atr"],
            "volume_ratio": prepared["tf_1h"]["volume_ratio"],
            "swing_high_1h": prepared["tf_1h"]["swing_high"],
            "swing_low_1h": prepared["tf_1h"]["swing_low"],
        },
    }
    resp = client.post("/thesis/submit", json=thesis)
    assert resp.status_code == 200
    return resp.json()["thesis"]["decision_id"], prepared


def _synthetic_candles(trend, n=300, volume_spike_at=None):
    step_pct = {"up": 0.05, "down": -0.05, "flat": 0.0}[trend]
    price = 50_000.0
    candles = []
    spike_index = n + volume_spike_at if (volume_spike_at is not None and volume_spike_at < 0) else volume_spike_at
    for i in range(n):
        open_ = price
        price = price * (1 + step_pct / 100)
        close = price
        wick = close * 0.3 / 100
        high = max(open_, close) + wick
        low = min(open_, close) - wick
        volume = 300.0 if spike_index is not None and i == spike_index else 100.0
        candles.append({"ts": "2024-01-01T00:00:00Z", "o": str(open_), "h": str(high), "l": str(low), "c": str(close), "vol": str(volume)})
    return candles


def _guard_intent_payload(thesis_id: str, prepared: dict, confidence: float = 0.75, **overrides):
    entry = prepared["tf_15m"]["price"]
    stop = prepared["tf_1h"]["swing_low"]
    payload = {
        "symbol": "BTC-USDT",
        "side": "buy",
        "order_type": "market",
        "requested_notional": "50",
        "requested_quantity": "0.001",
        "entry_price": entry,
        "invalidation": {"condition": "close below swing low", "price": stop},
        "target": {"price": str(float(entry) * 1.05)},
        "strategy": "trend_breakout",
        "strategy_version": "v1",
        "thesis_id": thesis_id,
        "confidence": confidence,
    }
    payload.update(overrides)
    return payload


def test_get_config_returns_active_policy(client: TestClient):
    resp = client.get("/guard/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["allowed_symbols"] == ["BTC-USDT"]
    assert body["max_notional_per_trade_usd"] == 100.0
    assert body["policy_version"] == "guard_v1_test"


def test_evaluate_approves_valid_intent(client: TestClient):
    thesis_id, prepared = _log_thesis(client, action="BUY", confidence=0.75)
    intent = _guard_intent_payload(thesis_id, prepared, confidence=0.75)
    resp = client.post("/guard/evaluate", json={"intent": intent, "account": _account_payload()})
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "APPROVE"


def test_evaluate_rejects_wait_thesis(client: TestClient):
    thesis_id, prepared = _log_thesis(client, action="WAIT", confidence=0.5)
    intent = _guard_intent_payload(thesis_id, prepared, confidence=0.5)
    resp = client.post("/guard/evaluate", json={"intent": intent, "account": _account_payload()})
    assert resp.status_code == 200
    assert resp.json()["decision"] == "REJECT"


def test_evaluate_rejects_unknown_thesis_id(client: TestClient):
    intent = _guard_intent_payload("does-not-exist", {"tf_15m": {"price": "50000"}, "tf_1h": {"swing_low": "48000"}})
    resp = client.post("/guard/evaluate", json={"intent": intent, "account": _account_payload()})
    assert resp.status_code == 200
    assert resp.json()["decision"] == "REJECT"
    assert any("thesis" in r.lower() for r in resp.json()["rejection_reasons"])


def test_evaluate_rejects_malformed_confidence(client: TestClient):
    thesis_id, prepared = _log_thesis(client)
    intent = _guard_intent_payload(thesis_id, prepared, confidence=5.0)
    resp = client.post("/guard/evaluate", json={"intent": intent, "account": _account_payload()})
    assert resp.status_code == 422


def test_duplicate_intent_second_submission_rejected(client: TestClient):
    thesis_id, prepared = _log_thesis(client, action="BUY", confidence=0.75)
    intent = _guard_intent_payload(thesis_id, prepared, confidence=0.75)
    first = client.post("/guard/evaluate", json={"intent": intent, "account": _account_payload()})
    assert first.json()["decision"] == "APPROVE"

    intent2 = _guard_intent_payload(thesis_id, prepared, confidence=0.75)
    second = client.post("/guard/evaluate", json={"intent": intent2, "account": _account_payload()})
    assert second.json()["decision"] == "REJECT"
    assert any("already been evaluated" in r for r in second.json()["rejection_reasons"])


def test_history_and_for_thesis_endpoints(client: TestClient):
    thesis_id, prepared = _log_thesis(client, action="BUY", confidence=0.75)
    intent = _guard_intent_payload(thesis_id, prepared, confidence=0.75)
    client.post("/guard/evaluate", json={"intent": intent, "account": _account_payload()})

    history = client.get("/guard/history", params={"symbol": "BTC-USDT"})
    assert history.status_code == 200
    assert len(history.json()) == 1

    for_thesis = client.get(f"/guard/for-thesis/{thesis_id}")
    assert for_thesis.status_code == 200
    assert for_thesis.json()["trade_intent"]["thesis_id"] == thesis_id


def test_latest_404_when_nothing_logged(client: TestClient):
    resp = client.get("/guard/latest", params={"symbol": "DOGE-USDT"})
    assert resp.status_code == 404
