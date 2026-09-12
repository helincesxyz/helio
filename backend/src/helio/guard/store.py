from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from helio.guard.models import SCHEMA_SQL
from helio.schemas.guard import GuardDecision, GuardRecord, GuardTradeIntent


class GuardStore:
    """Logs every risk evaluation — approved or rejected. This is the audit
    trail GATE 4 (execution) must consult before ever acting on an APPROVE,
    and the source of truth for duplicate-intent detection."""

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def log(self, intent: GuardTradeIntent, decision: GuardDecision) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO guard_events (trade_intent_id, thesis_id, symbol, decision, policy_version, "
                "trade_intent_json, decision_json, logged_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    intent.trade_intent_id,
                    intent.thesis_id,
                    intent.symbol,
                    decision.decision,
                    decision.policy_version,
                    intent.model_dump_json(),
                    decision.model_dump_json(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def exists_for_thesis(self, thesis_id: str) -> bool:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT 1 FROM guard_events WHERE thesis_id = ? LIMIT 1", (thesis_id,)).fetchone()
        return row is not None

    def get_recent(self, limit: int = 50) -> list[GuardRecord]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT trade_intent_id, trade_intent_json, decision_json, logged_at "
                "FROM guard_events ORDER BY logged_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_by_symbol(self, symbol: str, limit: int = 50) -> list[GuardRecord]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT trade_intent_id, trade_intent_json, decision_json, logged_at "
                "FROM guard_events WHERE symbol = ? ORDER BY logged_at DESC LIMIT ?",
                (symbol, limit),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_latest(self, symbol: str) -> GuardRecord | None:
        records = self.get_by_symbol(symbol, limit=1)
        return records[0] if records else None

    def get_by_trade_intent_id(self, trade_intent_id: str) -> GuardRecord | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT trade_intent_id, trade_intent_json, decision_json, logged_at "
                "FROM guard_events WHERE trade_intent_id = ?",
                (trade_intent_id,),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def get_by_thesis_id(self, thesis_id: str) -> GuardRecord | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT trade_intent_id, trade_intent_json, decision_json, logged_at "
                "FROM guard_events WHERE thesis_id = ? ORDER BY logged_at DESC LIMIT 1",
                (thesis_id,),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def self_test(self) -> bool:
        test_id = f"selftest-{datetime.now(timezone.utc).timestamp()}"
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO guard_events (trade_intent_id, thesis_id, symbol, decision, policy_version, "
                "trade_intent_json, decision_json, logged_at) VALUES (?, 'HELIO_SELFTEST', 'BTC-USDT', "
                "'REJECT', 'guard_v1', '{}', '{}', ?)",
                (test_id, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            row = conn.execute("SELECT trade_intent_id FROM guard_events WHERE trade_intent_id = ?", (test_id,)).fetchone()
            conn.execute("DELETE FROM guard_events WHERE trade_intent_id = ?", (test_id,))
            conn.commit()
        return row is not None

    @staticmethod
    def _row_to_record(row: tuple) -> GuardRecord:
        trade_intent_id, trade_intent_json, decision_json, logged_at = row
        return GuardRecord(
            trade_intent_id=trade_intent_id,
            logged_at=logged_at,
            trade_intent=GuardTradeIntent.model_validate_json(trade_intent_json),
            decision=GuardDecision.model_validate_json(decision_json),
        )
