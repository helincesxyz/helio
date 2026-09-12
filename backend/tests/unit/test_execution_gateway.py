from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from helio.execution.gateway import ExecutionGateway, InvalidStateError, KillSwitchError, NotFoundError
from helio.execution.store import ExecutionStore
from helio.guard.context import GuardContext
from helio.guard.engine import GuardEngine
from helio.guard.store import GuardStore
from helio.schemas.account import AccountState, Balance
from helio.schemas.execution import ExecutionSubmissionIn, ExecutionVerifyRequest, OrderState


@pytest.fixture
def guard_store(tmp_path: Path) -> GuardStore:
    return GuardStore(tmp_path / "guard.sqlite3")


@pytest.fixture
def gateway(tmp_path: Path, guard_store: GuardStore) -> ExecutionGateway:
    return ExecutionGateway(ExecutionStore(tmp_path / "execution.sqlite3"), guard_store)


def _approve(guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
    engine = GuardEngine(guard_config)
    thesis = make_thesis_record()
    intent = make_guard_intent(thesis_record=thesis)
    ctx = GuardContext(account=make_account(), thesis_record=thesis, is_duplicate=False)
    decision = engine.evaluate(intent, ctx)
    assert decision.decision == "APPROVE"
    guard_store.log(intent, decision)
    return intent


def _reject(guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
    engine = GuardEngine(guard_config)
    thesis = make_thesis_record(action="WAIT")
    intent = make_guard_intent(thesis_record=thesis)
    ctx = GuardContext(account=make_account(), thesis_record=thesis, is_duplicate=False)
    decision = engine.evaluate(intent, ctx)
    assert decision.decision == "REJECT"
    guard_store.log(intent, decision)
    return intent


def _account_state(**overrides) -> AccountState:
    defaults = dict(mode="simulation", balances=[Balance(ccy="USDT", avail="950", total="950")], positions=[])
    defaults.update(overrides)
    return AccountState(**defaults)


class TestAuthorize:
    def test_approved_intent_can_be_authorized(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
        intent = _approve(guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        auth = gateway.authorize(intent.trade_intent_id, "execution_test")
        assert auth.trade_intent_id == intent.trade_intent_id
        assert auth.consumed is False
        assert auth.expires_at > auth.authorized_at

    def test_rejected_intent_cannot_be_authorized(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
        intent = _reject(guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        with pytest.raises(InvalidStateError):
            gateway.authorize(intent.trade_intent_id, "execution_test")

    def test_unknown_trade_intent_id_raises_not_found(self, gateway):
        with pytest.raises(NotFoundError):
            gateway.authorize("does-not-exist", "execution_test")

    def test_second_authorization_for_same_intent_is_rejected(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
        intent = _approve(guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        gateway.authorize(intent.trade_intent_id, "execution_test")
        with pytest.raises(InvalidStateError):
            gateway.authorize(intent.trade_intent_id, "execution_test")


class TestPrepare:
    def test_prepare_returns_exact_order_params(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
        intent = _approve(guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        auth = gateway.authorize(intent.trade_intent_id, "execution_test")
        prep = gateway.prepare(auth.execution_id, "simulation")
        assert prep.instId == intent.symbol
        assert prep.side == intent.side
        assert prep.sz == intent.requested_quantity
        assert prep.simulatedTrading is True
        assert prep.tgtCcy == "base_ccy"  # sz is BTC quantity, never quote-currency

    def test_prepare_unknown_execution_id_raises_not_found(self, gateway):
        with pytest.raises(NotFoundError):
            gateway.prepare("does-not-exist", "simulation")

    def test_prepare_live_blocked_when_kill_switch_off(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account, monkeypatch):
        monkeypatch.delenv("HELIO_LIVE_EXECUTION_ENABLED", raising=False)
        intent = _approve(guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        auth = gateway.authorize(intent.trade_intent_id, "execution_test")
        with pytest.raises(KillSwitchError):
            gateway.prepare(auth.execution_id, "live")

    def test_prepare_live_allowed_when_kill_switch_on(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account, monkeypatch):
        monkeypatch.setenv("HELIO_LIVE_EXECUTION_ENABLED", "true")
        intent = _approve(guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        auth = gateway.authorize(intent.trade_intent_id, "execution_test")
        prep = gateway.prepare(auth.execution_id, "live")
        assert prep.simulatedTrading is False

    def test_expired_authorization_cannot_be_prepared(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
        intent = _approve(guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        auth = gateway.authorize(intent.trade_intent_id, "execution_test")

        lifecycle = gateway.get(auth.execution_id)
        lifecycle.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        gateway._store.update(lifecycle)  # simulate time passing

        with pytest.raises(InvalidStateError):
            gateway.prepare(auth.execution_id, "simulation")


class TestRecordSubmission:
    def test_accepted_submission_marks_submitted_and_consumed(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
        intent = _approve(guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        auth = gateway.authorize(intent.trade_intent_id, "execution_test")
        gateway.prepare(auth.execution_id, "simulation")

        result = gateway.record_submission(
            ExecutionSubmissionIn(execution_id=auth.execution_id, okx_order_id="okx-1", okx_code="0", okx_scode="0")
        )
        assert result.status == "SUBMITTED"

        lifecycle = gateway.get(auth.execution_id)
        assert lifecycle.consumed is True

    def test_rejected_okx_response_marks_rejected(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
        intent = _approve(guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        auth = gateway.authorize(intent.trade_intent_id, "execution_test")
        gateway.prepare(auth.execution_id, "simulation")

        result = gateway.record_submission(
            ExecutionSubmissionIn(execution_id=auth.execution_id, okx_code="1", okx_scode="51008", okx_message="insufficient balance")
        )
        assert result.status == "REJECTED"

    def test_submission_without_prepare_raises(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
        intent = _approve(guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        auth = gateway.authorize(intent.trade_intent_id, "execution_test")
        with pytest.raises(InvalidStateError):
            gateway.record_submission(ExecutionSubmissionIn(execution_id=auth.execution_id, okx_code="0"))

    def test_double_submission_is_rejected(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
        intent = _approve(guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        auth = gateway.authorize(intent.trade_intent_id, "execution_test")
        gateway.prepare(auth.execution_id, "simulation")
        gateway.record_submission(ExecutionSubmissionIn(execution_id=auth.execution_id, okx_code="0"))

        with pytest.raises(InvalidStateError):
            gateway.record_submission(ExecutionSubmissionIn(execution_id=auth.execution_id, okx_code="0"))


class TestVerify:
    def _submitted(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
        intent = _approve(guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        auth = gateway.authorize(intent.trade_intent_id, "execution_test")
        gateway.prepare(auth.execution_id, "simulation")
        gateway.record_submission(ExecutionSubmissionIn(execution_id=auth.execution_id, okx_order_id="okx-1", okx_code="0"))
        return auth

    def test_filled_order_finalizes_lifecycle(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
        auth = self._submitted(gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        lifecycle = gateway.verify(
            ExecutionVerifyRequest(
                execution_id=auth.execution_id,
                order_state=OrderState(okx_order_id="okx-1", state="filled", filled_quantity="0.001", avg_fill_price="50000"),
                account_state_after=_account_state(),
            )
        )
        assert lifecycle.status == "FILLED"
        assert lifecycle.verified_at is not None
        assert lifecycle.account_state_after is not None

    def test_unknown_order_state_is_terminal_unknown(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
        auth = self._submitted(gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        lifecycle = gateway.verify(
            ExecutionVerifyRequest(
                execution_id=auth.execution_id,
                order_state=OrderState(okx_order_id="okx-1", state="unknown"),
                account_state_after=_account_state(),
            )
        )
        assert lifecycle.status == "UNKNOWN"

    def test_verify_before_submission_raises(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
        intent = _approve(guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        auth = gateway.authorize(intent.trade_intent_id, "execution_test")
        with pytest.raises(InvalidStateError):
            gateway.verify(
                ExecutionVerifyRequest(
                    execution_id=auth.execution_id,
                    order_state=OrderState(okx_order_id="okx-1", state="filled"),
                    account_state_after=_account_state(),
                )
            )

    def test_double_verify_is_rejected_no_reretry(self, gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account):
        auth = self._submitted(gateway, guard_store, guard_config, make_guard_intent, make_thesis_record, make_account)
        gateway.verify(
            ExecutionVerifyRequest(
                execution_id=auth.execution_id,
                order_state=OrderState(okx_order_id="okx-1", state="unknown"),
                account_state_after=_account_state(),
            )
        )
        with pytest.raises(InvalidStateError):
            gateway.verify(
                ExecutionVerifyRequest(
                    execution_id=auth.execution_id,
                    order_state=OrderState(okx_order_id="okx-1", state="filled"),
                    account_state_after=_account_state(),
                )
            )
