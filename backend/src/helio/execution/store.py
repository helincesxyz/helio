from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from helio.execution.models import SCHEMA_SQL
from helio.schemas.execution import ExecutionLifecycle


class DuplicateAuthorizationError(Exception):
    """Raised when a trade_intent_id already has an execution row — the
    DB's UNIQUE constraint is the actual enforcement; this just gives the
    caller a clean exception instead of a raw sqlite3.IntegrityError."""


class ExecutionStore:
    """One row per execution attempt, keyed by execution_id, with a UNIQUE
    constraint on trade_intent_id: a second authorization attempt for a
    trade intent that already has one is rejected by the database itself,
    not just application logic — see docs/EXECUTION_PROTOCOL.md."""

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def create(self, lifecycle: ExecutionLifecycle) -> None:
        try:
            with closing(self._connect()) as conn:
                conn.execute(
                    "INSERT INTO execution_events (execution_id, trade_intent_id, thesis_id, status, "
                    "lifecycle_json, authorized_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        lifecycle.execution_id,
                        lifecycle.trade_intent_id,
                        lifecycle.thesis_id,
                        lifecycle.status,
                        lifecycle.model_dump_json(),
                        lifecycle.authorized_at.isoformat(),
                    ),
                )
                conn.commit()
        except sqlite3.IntegrityError as exc:
            raise DuplicateAuthorizationError(
                f"trade intent {lifecycle.trade_intent_id!r} already has an execution authorization"
            ) from exc

    def update(self, lifecycle: ExecutionLifecycle) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE execution_events SET status = ?, lifecycle_json = ? WHERE execution_id = ?",
                (lifecycle.status, lifecycle.model_dump_json(), lifecycle.execution_id),
            )
            conn.commit()

    def get(self, execution_id: str) -> ExecutionLifecycle | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT lifecycle_json FROM execution_events WHERE execution_id = ?", (execution_id,)
            ).fetchone()
        return ExecutionLifecycle.model_validate_json(row[0]) if row else None

    def get_by_trade_intent_id(self, trade_intent_id: str) -> ExecutionLifecycle | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT lifecycle_json FROM execution_events WHERE trade_intent_id = ?", (trade_intent_id,)
            ).fetchone()
        return ExecutionLifecycle.model_validate_json(row[0]) if row else None

    def get_by_thesis_id(self, thesis_id: str) -> list[ExecutionLifecycle]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT lifecycle_json FROM execution_events WHERE thesis_id = ? ORDER BY authorized_at DESC",
                (thesis_id,),
            ).fetchall()
        return [ExecutionLifecycle.model_validate_json(row[0]) for row in rows]

    def get_recent(self, limit: int = 50) -> list[ExecutionLifecycle]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT lifecycle_json FROM execution_events ORDER BY authorized_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [ExecutionLifecycle.model_validate_json(row[0]) for row in rows]

    def self_test(self) -> bool:
        from datetime import datetime, timedelta, timezone

        test_id = f"HELIO_SELFTEST_EXECUTION_{datetime.now(timezone.utc).timestamp()}"
        now = datetime.now(timezone.utc)
        lifecycle = ExecutionLifecycle(
            execution_id=test_id,
            trade_intent_id=test_id,
            thesis_id="selftest",
            risk_evaluation_id="selftest",
            intent_hash="selftest",
            origin="execution_test",
            requested_quantity="0",
            expires_at=now + timedelta(minutes=5),
            authorized_at=now,
        )
        self.create(lifecycle)
        fetched = self.get(test_id)
        with closing(self._connect()) as conn:
            conn.execute("DELETE FROM execution_events WHERE execution_id = ?", (test_id,))
            conn.commit()
        return fetched is not None
