from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from helio.conversation.models import SCHEMA_SQL
from helio.schemas.conversation import ConversationRequest, ConversationResponse


class ConversationStore:
    """Persists every conversation-bridge request — pending, answered, or
    failed — so the UI can poll for an answer and the fulfillment side
    (Claude Code, per docs/runbooks/conversation_fulfillment.md) can find
    what's waiting. Same shape as ThesisStore/GuardStore."""

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def create(self, request: ConversationRequest) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO conversation_events (request_id, conversation_id, message, intent, "
                "risk_profile, status, created_at, response_json) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
                (
                    request.request_id,
                    request.conversation_id,
                    request.message,
                    request.intent,
                    request.risk_profile,
                    request.status,
                    request.created_at.isoformat(),
                ),
            )
            conn.commit()

    def get_by_id(self, request_id: str) -> ConversationRequest | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT request_id, conversation_id, message, intent, risk_profile, status, "
                "created_at, response_json FROM conversation_events WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def get_pending(self, limit: int = 50) -> list[ConversationRequest]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT request_id, conversation_id, message, intent, risk_profile, status, "
                "created_at, response_json FROM conversation_events WHERE status = 'PENDING' "
                "ORDER BY created_at ASC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def respond(self, request_id: str, response: ConversationResponse) -> ConversationRequest:
        """The only way a response gets attached. Fails closed: rejects if
        the request doesn't exist, or has already been answered/failed —
        no double-answer, no silently overwriting a prior result."""
        existing = self.get_by_id(request_id)
        if existing is None:
            raise KeyError(f"no conversation request {request_id!r}")
        if existing.status != "PENDING":
            raise ValueError(f"conversation request {request_id!r} is already {existing.status}")

        new_status = "FAILED" if response.kind == "error" else "ANSWERED"
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE conversation_events SET status = ?, response_json = ? WHERE request_id = ?",
                (new_status, response.model_dump_json(), request_id),
            )
            conn.commit()
        updated = self.get_by_id(request_id)
        assert updated is not None
        return updated

    def self_test(self) -> bool:
        test_id = f"HELIO_SELFTEST_CONVERSATION_{datetime.now(timezone.utc).timestamp()}"
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO conversation_events (request_id, conversation_id, message, intent, "
                "risk_profile, status, created_at, response_json) VALUES (?, 'selftest', 'test', "
                "'UNKNOWN', 'balanced', 'PENDING', ?, NULL)",
                (test_id, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            row = conn.execute(
                "SELECT request_id FROM conversation_events WHERE request_id = ?", (test_id,)
            ).fetchone()
            conn.execute("DELETE FROM conversation_events WHERE request_id = ?", (test_id,))
            conn.commit()
        return row is not None

    @staticmethod
    def _row_to_record(row: tuple) -> ConversationRequest:
        request_id, conversation_id, message, intent, risk_profile, status, created_at, response_json = row
        response = ConversationResponse.model_validate_json(response_json) if response_json else None
        return ConversationRequest(
            request_id=request_id,
            conversation_id=conversation_id,
            message=message,
            intent=intent,
            risk_profile=risk_profile,
            status=status,
            created_at=created_at,
            response=response,
        )
