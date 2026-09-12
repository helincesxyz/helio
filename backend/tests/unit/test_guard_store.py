from __future__ import annotations

from pathlib import Path

from helio.guard.context import GuardContext
from helio.guard.engine import GuardEngine
from helio.guard.store import GuardStore


def test_log_and_retrieve_decision(tmp_path: Path, make_guard_intent, make_thesis_record, make_account, guard_config):
    store = GuardStore(tmp_path / "guard.sqlite3")
    engine = GuardEngine(guard_config)
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis)
    ctx = GuardContext(account=make_account(), thesis_record=thesis, is_duplicate=False)

    decision = engine.evaluate(intent, ctx)
    store.log(intent, decision)

    latest = store.get_latest("BTC-USDT")
    assert latest is not None
    assert latest.trade_intent_id == intent.trade_intent_id
    assert latest.decision.decision == "APPROVE"


def test_exists_for_thesis_detects_duplicates(
    tmp_path: Path, make_guard_intent, make_thesis_record, make_account, guard_config
):
    store = GuardStore(tmp_path / "guard.sqlite3")
    engine = GuardEngine(guard_config)
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis)
    ctx = GuardContext(account=make_account(), thesis_record=thesis, is_duplicate=False)

    assert store.exists_for_thesis(thesis.decision_id) is False
    decision = engine.evaluate(intent, ctx)
    store.log(intent, decision)
    assert store.exists_for_thesis(thesis.decision_id) is True


def test_get_by_thesis_id(tmp_path: Path, make_guard_intent, make_thesis_record, make_account, guard_config):
    store = GuardStore(tmp_path / "guard.sqlite3")
    engine = GuardEngine(guard_config)
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis)
    ctx = GuardContext(account=make_account(), thesis_record=thesis, is_duplicate=False)
    decision = engine.evaluate(intent, ctx)
    store.log(intent, decision)

    record = store.get_by_thesis_id(thesis.decision_id)
    assert record is not None
    assert record.trade_intent.thesis_id == thesis.decision_id


def test_self_test_round_trips_and_cleans_up(tmp_path: Path):
    store = GuardStore(tmp_path / "guard.sqlite3")
    assert store.self_test() is True
    assert store.get_by_symbol("BTC-USDT") == []
