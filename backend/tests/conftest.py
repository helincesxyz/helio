from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from helio.risk.config_loader import RiskConfig, load_risk_config
from helio.schemas.account import AccountState, Balance
from helio.schemas.market import Candle
from helio.schemas.trade_intent import TradeIntent

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def risk_config() -> RiskConfig:
    return load_risk_config(FIXTURES_DIR / "sample_risk_config.yaml")


@pytest.fixture
def make_intent():
    def _make(**overrides) -> TradeIntent:
        defaults = dict(
            strategy_id="test_strategy",
            symbol="BTC-USDT",
            instrument_type="SPOT",
            side="buy",
            order_type="market",
            size="50",
            size_unit="quote_ccy",
            rationale="test",
            mode="simulation",
            source="manual",
        )
        defaults.update(overrides)
        return TradeIntent(**defaults)

    return _make


@pytest.fixture
def make_account():
    def _make(**overrides) -> AccountState:
        defaults = dict(
            mode="simulation",
            balances=[Balance(ccy="USDT", avail="1000", total="1000")],
            positions=[],
        )
        defaults.update(overrides)
        return AccountState(**defaults)

    return _make


@pytest.fixture
def make_candles():
    """Deterministic synthetic OHLCV generator for exercising the thesis
    engine without hand-writing 250+ row fixtures. `trend` sets a small
    per-bar drift (up/down/flat); `volatility_pct` sets the wick size as a
    % of close (roughly controls ATR%); `volume_spike_at` multiplies one
    bar's volume by 3x (use -1 for "the latest/breakout bar") to control
    the breakout-volume-confirmation evidence gate.
    """

    def _make(
        n: int = 260,
        trend: str = "flat",
        start_price: float = 50_000.0,
        volatility_pct: float = 0.3,
        volume_spike_at: int | None = None,
        base_volume: float = 100.0,
        bar_minutes: int = 60,
    ) -> list[Candle]:
        step_pct = {"up": 0.05, "down": -0.05, "flat": 0.0}[trend]
        base_ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        candles: list[Candle] = []
        price = start_price
        spike_index = n + volume_spike_at if (volume_spike_at is not None and volume_spike_at < 0) else volume_spike_at
        for i in range(n):
            open_ = price
            price = price * (1 + step_pct / 100)
            close = price
            wick = close * volatility_pct / 100
            high = max(open_, close) + wick
            low = min(open_, close) - wick
            volume = base_volume * 3.0 if spike_index is not None and i == spike_index else base_volume
            candles.append(
                Candle(
                    ts=base_ts + timedelta(minutes=bar_minutes * i),
                    o=str(open_),
                    h=str(high),
                    l=str(low),
                    c=str(close),
                    vol=str(volume),
                )
            )
        return candles

    return _make
