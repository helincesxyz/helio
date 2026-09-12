from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from helio.schemas.thesis import PreparedMarketState, Thesis, ThesisRecord, ThesisValidationResult
from helio.thesis.models import SCHEMA_SQL


class ThesisStore:
    """Logs every reasoning cycle — GATE 3/4 will reuse these records, so
    every field the spec calls out (market state, strategy, signals, thesis,
    action, confidence, invalidation, target, evidence, decision id) is
    captured, valid or not."""

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def log(self, thesis: Thesis, prepared_state: PreparedMarketState, validation: ThesisValidationResult) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO thesis_events (decision_id, symbol, strategy, strategy_version, regime, "
                "action, confidence, valid, prepared_state_json, thesis_json, validation_json, logged_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    thesis.decision_id,
                    thesis.symbol,
                    thesis.strategy,
                    thesis.strategy_version,
                    thesis.regime,
                    thesis.action,
                    thesis.confidence,
                    1 if validation.valid else 0,
                    prepared_state.model_dump_json(),
                    thesis.model_dump_json(),
                    validation.model_dump_json(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def get_recent(self, limit: int = 50) -> list[ThesisRecord]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT decision_id, thesis_json, prepared_state_json, validation_json, logged_at "
                "FROM thesis_events ORDER BY logged_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_by_symbol(self, symbol: str, limit: int = 50) -> list[ThesisRecord]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT decision_id, thesis_json, prepared_state_json, validation_json, logged_at "
                "FROM thesis_events WHERE symbol = ? ORDER BY logged_at DESC LIMIT ?",
                (symbol, limit),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_latest(self, symbol: str) -> ThesisRecord | None:
        records = self.get_by_symbol(symbol, limit=1)
        return records[0] if records else None

    def get_by_id(self, decision_id: str) -> ThesisRecord | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT decision_id, thesis_json, prepared_state_json, validation_json, logged_at "
                "FROM thesis_events WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def self_test(self) -> bool:
        test_id = f"selftest-{datetime.now(timezone.utc).timestamp()}"
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO thesis_events (decision_id, symbol, strategy, strategy_version, regime, "
                "action, confidence, valid, prepared_state_json, thesis_json, validation_json, logged_at) "
                "VALUES (?, 'HELIO_SELFTEST', 'trend_breakout', 'v1', 'RANGE', 'WAIT', 0, 1, '{}', '{}', '{}', ?)",
                (test_id, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            row = conn.execute("SELECT decision_id FROM thesis_events WHERE decision_id = ?", (test_id,)).fetchone()
            conn.execute("DELETE FROM thesis_events WHERE decision_id = ?", (test_id,))
            conn.commit()
        return row is not None

    @staticmethod
    def _row_to_record(row: tuple) -> ThesisRecord:
        decision_id, thesis_json, prepared_state_json, validation_json, logged_at = row
        return ThesisRecord(
            decision_id=decision_id,
            logged_at=logged_at,
            thesis=Thesis.model_validate_json(thesis_json),
            prepared_state=PreparedMarketState.model_validate_json(prepared_state_json),
            validation=ThesisValidationResult.model_validate_json(validation_json),
        )
