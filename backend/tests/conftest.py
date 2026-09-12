from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from helio.guard.config import GuardConfig, load_guard_config
from helio.risk.config_loader import RiskConfig, load_risk_config
from helio.schemas.account import AccountState, Balance
from helio.schemas.guard import GuardTradeIntent, Invalidation as GuardInvalidation, Target as GuardTarget
from helio.schemas.market import Candle
from helio.schemas.thesis import (
    EvidenceItem,
    PreparedMarketState,
    Thesis,
    ThesisMarketStateEcho,
    ThesisRecord,
    ThesisValidationResult,
    TimeframeIndicators,
)
from helio.schemas.trade_intent import TradeIntent

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def risk_config() -> RiskConfig:
    return load_risk_config(FIXTURES_DIR / "sample_risk_config.yaml")


@pytest.fixture
def guard_config() -> GuardConfig:
    return load_guard_config(FIXTURES_DIR / "sample_guard_config.yaml")


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
            daily_realized_pnl_usd="0",
        )
        defaults.update(overrides)
        return AccountState(**defaults)

    return _make


def _tf_indicators(timeframe: str, **overrides) -> TimeframeIndicators:
    defaults = dict(
        timeframe=timeframe,
        candle_count=300,
        price="50000",
        ema20="49000",
        ema50="48000",
        ema200="47000",
        atr="500",
        atr_pct="1.0",
        volume="100",
        volume_avg="80",
        volume_ratio="1.5",
        swing_high="50500",
        swing_low="48500",
        price_change_pct="2.0",
    )
    defaults.update(overrides)
    return TimeframeIndicators(**defaults)


@pytest.fixture
def make_thesis_record():
    def _make(**overrides) -> ThesisRecord:
        decision_id = overrides.pop("decision_id", str(uuid.uuid4()))
        symbol = overrides.pop("symbol", "BTC-USDT")
        action = overrides.pop("action", "BUY")
        regime = overrides.pop("regime", "BULL_TREND")
        confidence = overrides.pop("confidence", 0.75)
        valid = overrides.pop("valid", True)
        validation_errors = overrides.pop("validation_errors", [])
        prepared_at = overrides.pop("prepared_at", datetime.now(timezone.utc))

        prepared_state = PreparedMarketState(
            symbol=symbol,
            prepared_at=prepared_at,
            tf_4h=_tf_indicators("4H"),
            tf_1h=_tf_indicators("1H"),
            tf_15m=_tf_indicators("15m"),
            regime=regime,
            regime_reason="test fixture",
            evidence=[EvidenceItem(name="trend_structure_bullish_4h", passed=True, detail="test", hard_gate=True)],
            candidate_action=action,
        )
        thesis = Thesis(
            decision_id=decision_id,
            symbol=symbol,
            regime=regime,
            action=action,
            confidence=confidence,
            thesis="test thesis",
            evidence=["test evidence"],
            invalidation=None,
            target=None,
            market_state=ThesisMarketStateEcho(
                price="50000",
                ema20_4h="49000",
                ema50_4h="48000",
                ema200_4h="47000",
                atr_1h="500",
                volume_ratio="1.5",
                swing_high_1h="50500",
                swing_low_1h="48500",
            ),
        )
        validation = ThesisValidationResult(valid=valid, errors=validation_errors)
        return ThesisRecord(
            decision_id=decision_id,
            logged_at=prepared_at,
            thesis=thesis,
            prepared_state=prepared_state,
            validation=validation,
        )

    return _make


@pytest.fixture
def make_guard_intent():
    def _make(thesis_record=None, **overrides) -> GuardTradeIntent:
        defaults = dict(
            symbol="BTC-USDT",
            side="buy",
            order_type="market",
            instrument_type="SPOT",
            leverage=None,
            requested_notional="50",
            requested_quantity="0.001",
            entry_price="50000",
            invalidation=GuardInvalidation(condition="close below 1H swing low", price="48500"),
            target=GuardTarget(price="53000"),
            strategy="trend_breakout",
            strategy_version="v1",
            thesis_id=thesis_record.decision_id if thesis_record else str(uuid.uuid4()),
            confidence=thesis_record.thesis.confidence if thesis_record else 0.75,
        )
        defaults.update(overrides)
        return GuardTradeIntent(**defaults)

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
