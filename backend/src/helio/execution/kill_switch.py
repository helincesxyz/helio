"""The one deterministic gate a live execution can never bypass.

`HELIO_LIVE_EXECUTION_ENABLED` is an environment variable, never a request
body field — no LLM output, no API payload, no "trust me" flag anywhere in
this codebase can flip it. It's read fresh on every check (never cached),
so flipping it in the environment takes effect immediately without a
restart, and defaults to OFF.
"""
from __future__ import annotations

import os

_ENV_VAR = "HELIO_LIVE_EXECUTION_ENABLED"
_TRUE_VALUES = {"1", "true", "yes", "on"}


def live_execution_enabled() -> bool:
    return os.environ.get(_ENV_VAR, "").strip().lower() in _TRUE_VALUES
