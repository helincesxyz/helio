"""Structured logging with a defense-in-depth secret redaction filter.

No legitimate Helio code path should ever produce an OKX credential in a log
line (see SECURITY.md) — this filter exists purely as a second layer of
protection in case a future contributor's code accidentally logs something
credential-shaped.
"""
from __future__ import annotations

import logging
import re

_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret[_-]?key|passphrase|private[_-]?key|seed)\s*[:=]\s*\S+"),
]
_REDACTED = "[REDACTED]"


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = message
        for pattern in _SECRET_PATTERNS:
            redacted = pattern.sub(lambda m: f"{m.group(1)}={_REDACTED}", redacted)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def configure_logging(level: str = "info") -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    root = logging.getLogger()
    for handler in root.handlers:
        handler.addFilter(RedactingFilter())
