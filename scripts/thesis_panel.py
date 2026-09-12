#!/usr/bin/env python3
"""Render the latest logged Thesis for a symbol as a terminal decision panel.

Only talks to Helio's own local API (GET /thesis/latest) — never to OKX
directly. Standard-library only, mirrors scripts/health_check.py.

Exit code: 0 if a thesis was found and rendered (WAIT is a normal outcome,
not a failure); 1 if the service is unreachable or nothing has been logged.
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
import urllib.error
import urllib.request

RULE = "━" * 24
PANEL_WIDTH = 28

# Human labels for each deterministic evidence gate, by outcome.
EVIDENCE_LABELS = {
    "trend_structure_bullish_4h": ("EMA20 > EMA50 > EMA200 (4H)", "4H trend structure not bullish"),
    "higher_high_structure_4h": ("Higher-high structure", "No higher-high structure"),
    "breakout_level_broken_or_approached_1h": ("1H breakout level reached", "1H breakout level not reached"),
    "breakout_volume_confirmed_1h": ("Breakout volume confirmed", "Breakout volume insufficient"),
    "entry_confirmation_not_chasing_15m": ("15m confirms without chasing", "15m price already extended (chasing)"),
    "volatility_not_abnormal_4h": ("Volatility normal", "Volatility abnormal"),
    "timeframes_consistent": ("Timeframes consistent", "Timeframes conflict"),
}


def _get_json(url: str, timeout: float) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.load(resp)


def _render(record: dict) -> str:
    thesis = record["thesis"]
    prepared = record["prepared_state"]

    regime_display = thesis["regime"].replace("_", " ").title()
    strategy_display = f"{thesis['strategy'].replace('_', ' ').title()} {thesis['strategy_version']}"

    evidence_lines = []
    needed_labels = []  # positive-phrased "what's needed" for each failed hard gate
    for item in prepared["evidence"]:
        good_label, bad_label = EVIDENCE_LABELS.get(item["name"], (item["name"], item["name"]))
        if item["passed"]:
            evidence_lines.append(f"✓ {good_label}")
        else:
            evidence_lines.append(f"✗ {bad_label}")
            if item["hard_gate"]:
                needed_labels.append(good_label)

    invalidation = thesis.get("invalidation")
    if invalidation and invalidation.get("price"):
        invalidation_line = f"Below ${invalidation['price']}"
    elif invalidation and invalidation.get("condition"):
        invalidation_line = invalidation["condition"]
    else:
        invalidation_line = "N/A — no active setup"

    if thesis["action"] == "BUY":
        next_condition = "None — thesis is already actionable"
    elif needed_labels:
        next_condition = " + ".join(needed_labels)
    else:
        next_condition = "Regime must turn Bull Trend before this strategy applies"

    lines = [
        RULE,
        "HELIO",
        thesis["symbol"],
        "",
        "REGIME",
        regime_display,
        "",
        "STRATEGY",
        strategy_display,
        "",
        "ACTION",
        thesis["action"],
        "",
        "CONFIDENCE",
        f"{thesis['confidence']:.2f}",
        "",
        "THESIS",
        textwrap.fill(thesis["thesis"], width=PANEL_WIDTH),
        "",
        "EVIDENCE",
        *evidence_lines,
        "",
        "INVALIDATION",
        invalidation_line,
        "",
        "NEXT CONDITION",
        next_condition,
        RULE,
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--symbol", default="BTC-USDT")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    url = f"{args.base_url}/thesis/latest?symbol={args.symbol}"
    try:
        record = _get_json(url, args.timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print(f"No thesis logged yet for {args.symbol}. Run /thesis/prepare + /thesis/submit first.")
            return 1
        print(f"Error fetching {url}: {exc}")
        return 1
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"Could not reach Helio service at {args.base_url}: {exc}")
        return 1

    print(_render(record))
    return 0


if __name__ == "__main__":
    sys.exit(main())
