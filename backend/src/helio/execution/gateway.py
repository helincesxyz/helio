from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from helio.execution.kill_switch import live_execution_enabled
from helio.execution.store import DuplicateAuthorizationError, ExecutionStore
from helio.guard.store import GuardStore
from helio.schemas.execution import (
    ExecutionAuthorization,
    ExecutionLifecycle,
    ExecutionOrigin,
    ExecutionPreparation,
    ExecutionResult,
    ExecutionSubmissionIn,
    ExecutionVerifyRequest,
)
from helio.schemas.guard import GuardTradeIntent

AUTHORIZATION_TTL = timedelta(minutes=5)


class ExecutionError(Exception):
    """Base for every gateway-rejected request. Routers translate these to
    the appropriate HTTP status — never a silent pass-through to OKX."""


class NotFoundError(ExecutionError):
    pass


class InvalidStateError(ExecutionError):
    """The requested transition doesn't apply to this execution's current
    state (already consumed, not yet prepared, expired, etc.)."""


class KillSwitchError(ExecutionError):
    pass


def _intent_hash(intent: GuardTradeIntent) -> str:
    return hashlib.sha256(intent.model_dump_json().encode("utf-8")).hexdigest()


class ExecutionGateway:
    """Gate 4: the only path from an APPROVEd GuardDecision to an actual
    OKX order. Every step here is real, exercised end-to-end in
    simulation. The live path is identical code — the only difference is
    the account owner submits the final order themselves; see
    docs/EXECUTION_PROTOCOL.md."""

    def __init__(self, store: ExecutionStore, guard_store: GuardStore):
        self._store = store
        self._guard_store = guard_store

    def authorize(self, trade_intent_id: str, origin: ExecutionOrigin) -> ExecutionAuthorization:
        record = self._guard_store.get_by_trade_intent_id(trade_intent_id)
        if record is None:
            raise NotFoundError(f"no guard decision found for trade_intent_id {trade_intent_id!r}")
        if record.decision.decision != "APPROVE":
            raise InvalidStateError(
                f"trade_intent_id {trade_intent_id!r} was REJECTed by Gate 3 — it can never be authorized"
            )

        now = datetime.now(timezone.utc)
        intent_hash = _intent_hash(record.trade_intent)
        execution_id = str(uuid.uuid4())
        lifecycle = ExecutionLifecycle(
            execution_id=execution_id,
            trade_intent_id=trade_intent_id,
            thesis_id=record.trade_intent.thesis_id,
            risk_evaluation_id=record.decision.decision_id,
            intent_hash=intent_hash,
            origin=origin,
            requested_quantity=record.trade_intent.requested_quantity,
            expires_at=now + AUTHORIZATION_TTL,
            authorized_at=now,
        )

        try:
            self._store.create(lifecycle)
        except DuplicateAuthorizationError as exc:
            raise InvalidStateError(str(exc)) from exc

        return ExecutionAuthorization(
            execution_id=lifecycle.execution_id,
            trade_intent_id=trade_intent_id,
            thesis_id=lifecycle.thesis_id,
            risk_evaluation_id=lifecycle.risk_evaluation_id,
            intent_hash=intent_hash,
            authorized_at=lifecycle.authorized_at,
            expires_at=lifecycle.expires_at,
            consumed=False,
        )

    def prepare(self, execution_id: str, mode: str) -> ExecutionPreparation:
        lifecycle = self._require(execution_id)
        self._require_unconsumed(lifecycle)
        self._require_unexpired(lifecycle)

        if mode == "live" and not live_execution_enabled():
            raise KillSwitchError(
                "live execution is disabled (HELIO_LIVE_EXECUTION_ENABLED is not set) — "
                "this is a deterministic, non-overridable gate"
            )

        record = self._guard_store.get_by_trade_intent_id(lifecycle.trade_intent_id)
        if record is None:
            raise NotFoundError(f"no guard decision found for trade_intent_id {lifecycle.trade_intent_id!r}")
        intent = record.trade_intent

        lifecycle.mode = mode  # type: ignore[assignment]
        lifecycle.prepared_at = datetime.now(timezone.utc)
        self._store.update(lifecycle)

        return ExecutionPreparation(
            execution_id=execution_id,
            mode=mode,  # type: ignore[arg-type]
            instId=intent.symbol,
            side=intent.side,
            ordType=intent.order_type,
            sz=intent.requested_quantity,
            simulatedTrading=(mode != "live"),
        )

    def record_submission(self, submission: ExecutionSubmissionIn) -> ExecutionResult:
        lifecycle = self._require(submission.execution_id)
        self._require_unconsumed(lifecycle)
        if lifecycle.prepared_at is None or lifecycle.mode is None:
            raise InvalidStateError("call /execution/prepare before recording a submission")

        accepted = submission.okx_code == "0" and (submission.okx_scode in (None, "0"))
        if accepted:
            status = "SUBMITTED" if lifecycle.mode == "simulation" else "LIVE"
        else:
            status = "REJECTED"

        lifecycle.status = status  # type: ignore[assignment]
        lifecycle.okx_order_id = submission.okx_order_id
        lifecycle.submitted_at = datetime.now(timezone.utc)
        lifecycle.consumed = True
        self._store.update(lifecycle)

        return ExecutionResult(
            execution_id=lifecycle.execution_id,
            okx_order_id=lifecycle.okx_order_id,
            status=lifecycle.status,
            requested_quantity=lifecycle.requested_quantity,
            mode=lifecycle.mode,
            origin=lifecycle.origin,
        )

    def verify(self, request: ExecutionVerifyRequest) -> ExecutionLifecycle:
        lifecycle = self._require(request.execution_id)
        if lifecycle.submitted_at is None:
            raise InvalidStateError("cannot verify an execution that was never submitted")
        if lifecycle.verified_at is not None:
            raise InvalidStateError(f"execution {lifecycle.execution_id!r} was already verified — no re-verification")

        state_to_status = {
            "filled": "FILLED",
            "partially_filled": "PARTIALLY_FILLED",
            "live": "LIVE",
            "canceled": "REJECTED",
            "unknown": "UNKNOWN",
        }
        final_status = state_to_status.get(request.order_state.state, "UNKNOWN")

        lifecycle.status = final_status  # type: ignore[assignment]
        lifecycle.filled_quantity = request.order_state.filled_quantity
        lifecycle.avg_fill_price = request.order_state.avg_fill_price
        lifecycle.fee = request.order_state.fee
        lifecycle.account_state_before = request.account_state_before
        lifecycle.account_state_after = request.account_state_after
        lifecycle.verified_at = datetime.now(timezone.utc)
        # UNKNOWN is terminal by construction: nothing below this line, or
        # anywhere else in the gateway, re-authorizes or retries from here.
        self._store.update(lifecycle)
        return lifecycle

    def get(self, execution_id: str) -> ExecutionLifecycle | None:
        return self._store.get(execution_id)

    def get_by_thesis_id(self, thesis_id: str) -> list[ExecutionLifecycle]:
        return self._store.get_by_thesis_id(thesis_id)

    def get_recent(self, limit: int = 50) -> list[ExecutionLifecycle]:
        return self._store.get_recent(limit=limit)

    def _require(self, execution_id: str) -> ExecutionLifecycle:
        lifecycle = self._store.get(execution_id)
        if lifecycle is None:
            raise NotFoundError(f"no execution {execution_id!r}")
        return lifecycle

    @staticmethod
    def _require_unconsumed(lifecycle: ExecutionLifecycle) -> None:
        if lifecycle.consumed:
            raise InvalidStateError(f"execution {lifecycle.execution_id!r} has already been submitted — no reuse")

    @staticmethod
    def _require_unexpired(lifecycle: ExecutionLifecycle) -> None:
        if datetime.now(timezone.utc) > lifecycle.expires_at:
            raise InvalidStateError(f"execution {lifecycle.execution_id!r} authorization has expired")
