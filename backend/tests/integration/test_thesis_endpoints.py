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
from helio.thesis.indicators import MIN_CANDLES_REQUIRED
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


def _candle_payload(n=300, trend="up", volatility_pct=0.3, volume_spike_at=None, bar_minutes=60):
    step_pct = {"up": 0.05, "down": -0.05, "flat": 0.0}[trend]
    price = 50_000.0
    candles = []
    spike_index = n + volume_spike_at if (volume_spike_at is not None and volume_spike_at < 0) else volume_spike_at
    for i in range(n):
        open_ = price
        price = price * (1 + step_pct / 100)
        close = price
        wick = close * volatility_pct / 100
        high = max(open_, close) + wick
        low = min(open_, close) - wick
        volume = 300.0 if spike_index is not None and i == spike_index else 100.0
        candles.append(
            {
                "ts": f"2024-01-01T{(i % 24):02d}:00:00Z" if bar_minutes >= 60 else "2024-01-01T00:00:00Z",
                "o": str(open_),
                "h": str(high),
                "l": str(low),
                "c": str(close),
                "vol": str(volume),
            }
        )
    return candles


def _bundle_payload(**kwargs):
    return {
        "symbol": "BTC-USDT",
        "tf_4h": _candle_payload(trend=kwargs.get("tf_4h_trend", "up")),
        "tf_1h": _candle_payload(trend=kwargs.get("tf_1h_trend", "up"), volume_spike_at=kwargs.get("volume_spike_at", -1)),
        "tf_15m": _candle_payload(trend=kwargs.get("tf_15m_trend", "up")),
    }


def test_prepare_returns_market_state(client: TestClient):
    resp = client.post("/thesis/prepare", json=_bundle_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "BTC-USDT"
    assert body["regime"] == "BULL_TREND"
    assert len(body["evidence"]) == 7


def test_prepare_with_insufficient_candles_is_422(client: TestClient):
    payload = _bundle_payload()
    payload["tf_4h"] = payload["tf_4h"][: MIN_CANDLES_REQUIRED - 1]
    resp = client.post("/thesis/prepare", json=payload)
    assert resp.status_code == 422


def test_submit_without_prepare_is_422(client: TestClient):
    thesis = {
        "symbol": "ETH-USDT",
        "regime": "RANGE",
        "action": "WAIT",
        "confidence": 0.5,
        "thesis": "no prior prepare call",
        "evidence": ["n/a"],
        "market_state": {},
    }
    resp = client.post("/thesis/submit", json=thesis)
    assert resp.status_code == 422


def test_submit_malformed_confidence_is_422(client: TestClient):
    client.post("/thesis/prepare", json=_bundle_payload())
    thesis = {
        "symbol": "BTC-USDT",
        "regime": "BULL_TREND",
        "action": "WAIT",
        "confidence": 5.0,
        "thesis": "bad confidence",
        "evidence": ["n/a"],
        "market_state": {},
    }
    resp = client.post("/thesis/submit", json=thesis)
    assert resp.status_code == 422


def test_full_prepare_submit_history_cycle(client: TestClient):
    prepared = client.post("/thesis/prepare", json=_bundle_payload(volume_spike_at=-1)).json()

    thesis = {
        "symbol": "BTC-USDT",
        "regime": prepared["regime"],
        "action": "BUY",
        "confidence": 0.75,
        "thesis": "Breakout with volume confirmation.",
        "evidence": [e["detail"] for e in prepared["evidence"]],
        "invalidation": {"condition": "Close back below 1H swing low", "price": prepared["tf_1h"]["swing_low"]},
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
    assert resp.json()["validation"]["valid"] is True

    latest = client.get("/thesis/latest", params={"symbol": "BTC-USDT"})
    assert latest.status_code == 200
    assert latest.json()["thesis"]["action"] == "BUY"

    history = client.get("/thesis/history", params={"symbol": "BTC-USDT"})
    assert history.status_code == 200
    assert len(history.json()) == 1


def test_latest_404_when_nothing_logged(client: TestClient):
    resp = client.get("/thesis/latest", params={"symbol": "DOGE-USDT"})
    assert resp.status_code == 404
