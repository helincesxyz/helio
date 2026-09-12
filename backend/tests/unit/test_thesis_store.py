from __future__ import annotations

from pathlib import Path

from helio.schemas.thesis import CandleBundle, Thesis, ThesisMarketStateEcho
from helio.thesis.prepare import prepare_market_state
from helio.thesis.store import ThesisStore
from helio.thesis.decision_quality import validate


def _record(make_candles):
    bundle = CandleBundle(
        symbol="BTC-USDT",
        tf_4h=make_candles(n=300, trend="flat", bar_minutes=240),
        tf_1h=make_candles(n=300, trend="flat", bar_minutes=60),
        tf_15m=make_candles(n=300, trend="flat", bar_minutes=15),
    )
    state = prepare_market_state(bundle)
    thesis = Thesis(
        symbol=state.symbol,
        regime=state.regime,
        action="WAIT",
        confidence=0.4,
        thesis="Ranging market, no setup.",
        evidence=[e.detail for e in state.evidence],
        market_state=ThesisMarketStateEcho(
            price=state.tf_15m.price,
            ema20_4h=state.tf_4h.ema20,
            ema50_4h=state.tf_4h.ema50,
            ema200_4h=state.tf_4h.ema200,
            atr_1h=state.tf_1h.atr,
            volume_ratio=state.tf_1h.volume_ratio,
            swing_high_1h=state.tf_1h.swing_high,
            swing_low_1h=state.tf_1h.swing_low,
        ),
    )
    validation = validate(thesis, state)
    return thesis, state, validation


def test_log_and_retrieve_thesis(tmp_path: Path, make_candles):
    store = ThesisStore(tmp_path / "thesis.sqlite3")
    thesis, state, validation = _record(make_candles)
    store.log(thesis, state, validation)

    latest = store.get_latest("BTC-USDT")
    assert latest is not None
    assert latest.decision_id == thesis.decision_id
    assert latest.thesis.action == "WAIT"
    assert latest.prepared_state.regime == state.regime
    assert latest.validation.valid == validation.valid


def test_get_by_symbol_and_recent(tmp_path: Path, make_candles):
    store = ThesisStore(tmp_path / "thesis.sqlite3")
    thesis, state, validation = _record(make_candles)
    store.log(thesis, state, validation)

    by_symbol = store.get_by_symbol("BTC-USDT")
    assert len(by_symbol) == 1

    recent = store.get_recent()
    assert len(recent) == 1

    assert store.get_by_symbol("ETH-USDT") == []


def test_self_test_round_trips_and_cleans_up(tmp_path: Path):
    store = ThesisStore(tmp_path / "thesis.sqlite3")
    assert store.self_test() is True
    assert store.get_by_symbol("HELIO_SELFTEST") == []
