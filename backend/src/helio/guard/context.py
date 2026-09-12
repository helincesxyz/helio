from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from helio.schemas.account import AccountState
from helio.schemas.thesis import ThesisRecord


@dataclass
class GuardContext:
    """Everything the GuardEngine needs besides the intent itself and the
    config. All of it must be independently verifiable — the engine never
    trusts a number the intent merely claims about itself (e.g. confidence
    is cross-checked against the linked thesis, not taken at face value)."""

    account: AccountState | None
    thesis_record: ThesisRecord | None
    is_duplicate: bool
    now: datetime = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.now is None:
            self.now = datetime.now(timezone.utc)
