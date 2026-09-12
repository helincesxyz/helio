#!/usr/bin/env python3
"""Visual demo of the GATE 3 guard engine: one APPROVED trade and one
REJECTED trade, rendered as a terminal panel. Standard-library only, talks
only to Helio's own local API (never to OKX directly) — mirrors
scripts/health_check.py and scripts/thesis_panel.py.

This script only calls /thesis/* and /guard/* on Helio's own service. It
never calls, and Helio never exposes, any order-placement/cancellation/
amendment or transfer/withdrawal capability.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request

RULE = "━" * 36


def _post(base_url: str, path: str, payload: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _synthetic_candles(trend: str, n: int = 300, volume_spike_at: int | None = None) -> list[dict]:
    step_pct = {"up": 0.05, "down": -0.05, "flat": 0.0}[trend]
    price = 50_000.0
    candles = []
    spike_index = n + volume_spike_at if (volume_spike_at is not None and volume_spike_at < 0) else volume_spike_at
    for i in range(n):
        open_ = price
        price = price * (1 + step_pct / 100)
        close = price
        wick = close * 0.3 / 100
        high = max(open_, close) + wick
        low = min(open_, close) - wick
        volume = 300.0 if spike_index is not None and i == spike_index else 100.0
        candles.append(
            {"ts": "2024-01-01T00:00:00Z", "o": str(open_), "h": str(high), "l": str(low), "c": str(close), "vol": str(volume)}
        )
    return candles


def _make_bullish_thesis(base_url: str, timeout: float, confidence: float) -> tuple[str, dict]:
    bundle = {
        "symbol": "BTC-USDT",
        "tf_4h": _synthetic_candles("up"),
        "tf_1h": _synthetic_candles("up", volume_spike_at=-1),
        "tf_15m": _synthetic_candles("up"),
    }
    prepared = _post(base_url, "/thesis/prepare", bundle, timeout)
    thesis = {
        "symbol": "BTC-USDT",
        "regime": prepared["regime"],
        "action": "BUY",
        "confidence": confidence,
        "thesis": "Demo thesis: synthetic bullish breakout with volume confirmation.",
        "evidence": [e["detail"] for e in prepared["evidence"]],
        "invalidation": {"condition": "Close back below the 1H swing low", "price": prepared["tf_1h"]["swing_low"]},
        "target": {"price": str(float(prepared["tf_15m"]["price"]) * 1.05)},
        "risk_reward": 2.0,
        "market_state": {
            "price": prepared["tf_15m"]["price"],
            "ema20_4h": prepared["tf_4h"]["ema20"],
            "ema50_4h": prepared["tf_4h"]["ema50"],
            "ema200_4h": prepared["tf_4h"]["ema200"],
            "atr_1h": prepared["tf_1h"]["atr"],
            "volume_ratio": prepared["tf_1h"]["volume_ratio"],
            "swing_high_1h": prepared["tf_1h"]["swing_high"],
            "swing_low_1h": prepared["tf_1h"]["swing_low"],
        },
    }
    result = _post(base_url, "/thesis/submit", thesis, timeout)
    return result["thesis"]["decision_id"], prepared


def _render_panel(intent: dict, decision: dict) -> str:
    lines = [RULE, "HELIO RISK ENGINE", ""]
    lines += [
        "Trade Intent",
        intent["symbol"],
        intent["side"].upper(),
        f"${float(intent['requested_notional']):.2f}",
        "",
        "Strategy",
        f"{intent['strategy'].replace('_', ' ').title()} {intent['strategy_version']}",
        "",
        "Confidence",
        f"{intent['confidence']:.2f}",
        "",
        "Risk Checks",
    ]
    for check in decision["checks"]:
        icon = "✓" if check["status"] == "PASS" else "✗"
        label = check["name"].replace("_", " ")
        lines.append(f"{icon} {label}")
    lines += ["", RULE, "", "RISK DECISION", ""]
    if decision["decision"] == "APPROVE":
        lines.append("   ✓ APPROVED")
    else:
        lines.append("   ✕ REJECTED")
        lines += ["", "Reasons:"]
        for reason in decision["rejection_reasons"]:
            lines.append(f"  • {reason}")
    lines += ["", RULE]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    print("=== DEMO 1: a conservative, well-formed trade ===\n")
    thesis_id, prepared = _make_bullish_thesis(args.base_url, args.timeout, confidence=0.78)
    approved_intent = {
        "symbol": "BTC-USDT",
        "side": "buy",
        "order_type": "market",
        "requested_notional": "5.00",
        "requested_quantity": str(round(5.00 / float(prepared["tf_15m"]["price"]), 8)),
        "entry_price": prepared["tf_15m"]["price"],
        "invalidation": {"condition": "Close back below the 1H swing low", "price": prepared["tf_1h"]["swing_low"]},
        "target": {"price": str(float(prepared["tf_15m"]["price"]) * 1.05)},
        "strategy": "trend_breakout",
        "strategy_version": "v1",
        "thesis_id": thesis_id,
        "confidence": 0.78,
    }
    account = {"mode": "simulation", "balances": [{"ccy": "USDT", "avail": "1000", "total": "1000"}], "positions": [], "daily_realized_pnl_usd": "0"}
    approved_decision = _post(args.base_url, "/guard/evaluate", {"intent": approved_intent, "account": account}, args.timeout)
    print(_render_panel(approved_intent, approved_decision))

    print("\n\n=== DEMO 2: an unsafe trade the risk engine must reject ===\n")
    thesis_id2, prepared2 = _make_bullish_thesis(args.base_url, args.timeout, confidence=0.9)
    rejected_intent = {
        "symbol": "BTC-USDT",
        "side": "buy",
        "order_type": "market",
        "requested_notional": "5000.00",  # exceeds max_notional_per_trade_usd
        "requested_quantity": str(round(5000.00 / float(prepared2["tf_15m"]["price"]), 8)),
        "entry_price": prepared2["tf_15m"]["price"],
        "invalidation": None,  # missing invalidation
        "target": {"price": str(float(prepared2["tf_15m"]["price"]) * 1.001)},  # negligible reward -> low RR
        "strategy": "trend_breakout",
        "strategy_version": "v1",
        "thesis_id": thesis_id2,
        "confidence": 0.9,
    }
    rejected_decision = _post(args.base_url, "/guard/evaluate", {"intent": rejected_intent, "account": account}, args.timeout)
    print(_render_panel(rejected_intent, rejected_decision))

    print(
        "\nNote: DEMO 2's AI-reported confidence was 0.9 (high) — the risk engine "
        "rejected it anyway, because policy limits are deterministic and do not "
        "defer to the AI's own confidence."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
