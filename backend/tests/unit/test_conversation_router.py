from __future__ import annotations

import pytest

from helio.conversation.intent import classify_intent


@pytest.mark.parametrize(
    "message,expected",
    [
        ("I want to get into BTC", "GET_INTO_BTC"),
        ("Get me into bitcoin", "GET_INTO_BTC"),
        ("I want to start investing", "GET_INTO_BTC"),
        ("Is there a good opportunity right now?", "GET_INTO_BTC"),
        ("Optimize my money", "OPTIMIZE_MONEY"),
        ("Can you put my money to work?", "OPTIMIZE_MONEY"),
        ("Optimize my APY using real OKX Earn discovery tools", "OPTIMIZE_APY"),
        ("What's the current earn yield on USDT?", "OPTIMIZE_APY"),
        ("What's the weather like today?", "UNKNOWN"),
        ("", "UNKNOWN"),
    ],
)
def test_classify_intent(message: str, expected: str) -> None:
    assert classify_intent(message) == expected


def test_apy_keyword_takes_priority_over_money_phrasing() -> None:
    # "optimize my money" phrasing alone would say OPTIMIZE_MONEY, but this
    # message is explicitly about yield — the more specific intent wins.
    assert classify_intent("optimize my money in an earn product") == "OPTIMIZE_APY"
