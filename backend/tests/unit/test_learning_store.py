from __future__ import annotations

from pathlib import Path

from helio.learning.store import EventStore
from helio.schemas.events import ExecutionResult, Outcome
from helio.schemas.risk_decision import RiskDecision


def test_log_and_retrieve_intent_and_decision(tmp_path: Path, make_intent):
    store = EventStore(tmp_path / "events.sqlite3")
    intent = make_intent()
    store.log_intent(intent)
    decision = RiskDecision(intent_id=intent.intent_id, approved=True, risk_config_hash="abc")
    store.log_decision(decision)

    events = store.get_recent()
    assert len(events) == 1
    assert events[0].intent.intent_id == intent.intent_id
    assert events[0].decision.approved is True


def test_log_execution_and_outcome(tmp_path: Path, make_intent):
    store = EventStore(tmp_path / "events.sqlite3")
    intent = make_intent()
    store.log_intent(intent)
    store.log_decision(RiskDecision(intent_id=intent.intent_id, approved=True, risk_config_hash="abc"))
    store.log_execution(intent.intent_id, ExecutionResult(ord_id="123", status="filled"))
    store.log_outcome(intent.intent_id, Outcome(realized_pnl_usd="5.00"))

    events = store.get_recent()
    assert events[0].execution_result.ord_id == "123"
    assert events[0].outcome.realized_pnl_usd == "5.00"


def test_get_by_strategy_filters(tmp_path: Path, make_intent):
    store = EventStore(tmp_path / "events.sqlite3")
    store.log_intent(make_intent(strategy_id="a"))
    store.log_intent(make_intent(strategy_id="b"))

    a_events = store.get_by_strategy("a")
    assert len(a_events) == 1
    assert a_events[0].intent.strategy_id == "a"


def test_self_test_round_trips_and_cleans_up(tmp_path: Path):
    store = EventStore(tmp_path / "events.sqlite3")
    assert store.self_test() is True
    # self_test should not leave rows behind
    assert store.get_by_strategy("helio_selftest") == []
