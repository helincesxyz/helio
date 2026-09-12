from __future__ import annotations

from pathlib import Path

import pytest

from helio.risk.config_loader import RiskConfig, load_risk_config
from helio.schemas.account import AccountState, Balance
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
