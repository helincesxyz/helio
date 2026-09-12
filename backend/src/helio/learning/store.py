from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from helio.learning.models import SCHEMA_SQL
from helio.schemas.events import ExecutionResult, LearningEvent, Outcome
from helio.schemas.risk_decision import RiskDecision
from helio.schemas.trade_intent import TradeIntent


class EventStore:
    """Append-only-ish log of every trade intent, its risk decision, and
    (eventually) its execution result and outcome. This is the real,
    working half of the learning engine — the analytical half
    (ParameterAdjuster) is a documented stub, see learning/adjuster.py."""

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def log_intent(self, intent: TradeIntent) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO learning_events (event_id, intent_id, strategy_id, intent_json, logged_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    intent.intent_id,
                    intent.intent_id,
                    intent.strategy_id,
                    intent.model_dump_json(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def log_decision(self, decision: RiskDecision) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE learning_events SET decision_json = ? WHERE intent_id = ?",
                (decision.model_dump_json(), decision.intent_id),
            )
            conn.commit()

    def log_execution(self, intent_id: str, result: ExecutionResult) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE learning_events SET execution_result_json = ? WHERE intent_id = ?",
                (result.model_dump_json(), intent_id),
            )
            conn.commit()

    def log_outcome(self, intent_id: str, outcome: Outcome) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE learning_events SET outcome_json = ? WHERE intent_id = ?",
                (outcome.model_dump_json(), intent_id),
            )
            conn.commit()

    def get_recent(self, limit: int = 50) -> list[LearningEvent]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT event_id, intent_json, decision_json, execution_result_json, outcome_json, logged_at "
                "FROM learning_events ORDER BY logged_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def get_by_strategy(self, strategy_id: str) -> list[LearningEvent]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT event_id, intent_json, decision_json, execution_result_json, outcome_json, logged_at "
                "FROM learning_events WHERE strategy_id = ? ORDER BY logged_at DESC",
                (strategy_id,),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def self_test(self) -> bool:
        """Round-trip a throwaway row to prove read/write works end-to-end.
        Used by the verification checklist; cleans up after itself."""
        test_id = f"selftest-{datetime.now(timezone.utc).timestamp()}"
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO learning_events (event_id, intent_id, strategy_id, intent_json, logged_at) "
                "VALUES (?, ?, 'helio_selftest', '{}', ?)",
                (test_id, test_id, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            row = conn.execute(
                "SELECT event_id FROM learning_events WHERE event_id = ?", (test_id,)
            ).fetchone()
            conn.execute("DELETE FROM learning_events WHERE event_id = ?", (test_id,))
            conn.commit()
        return row is not None

    @staticmethod
    def _row_to_event(row: tuple) -> LearningEvent:
        event_id, intent_json, decision_json, execution_json, outcome_json, logged_at = row
        return LearningEvent(
            event_id=event_id,
            intent=TradeIntent.model_validate_json(intent_json),
            decision=RiskDecision.model_validate_json(decision_json) if decision_json else _pending_decision(),
            execution_result=ExecutionResult.model_validate_json(execution_json) if execution_json else None,
            outcome=Outcome.model_validate_json(outcome_json) if outcome_json else None,
            logged_at=logged_at,
        )


def _pending_decision() -> RiskDecision:
    return RiskDecision(intent_id="pending", approved=False, reasons=["decision not yet logged"], risk_config_hash="")
