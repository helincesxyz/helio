from __future__ import annotations

from helio.schemas.conversation import Intent

# Deterministic, keyword-based intent classification — no ML, no guessing,
# same posture as thesis/regime.py's classifier. Order matters: APY/Earn
# phrasing and the explicit "optimize my money" phrasing are checked before
# the generic BTC/invest fallback so a specific request never gets
# swallowed by the broader one.
_APY_KEYWORDS = ("apy", "earn", "yield")
_MONEY_KEYWORDS = ("optimize my money", "put my money to work", "put money to work", "optimize money")
_BTC_KEYWORDS = ("btc", "bitcoin")
_GENERIC_INVEST_KEYWORDS = ("invest", "opportunity", "get into", "get me into")

# "Why?" follow-ups are handled entirely client-side (they re-explain an
# already-loaded thesis) — they never reach this router or the bridge.


def classify_intent(message: str) -> Intent:
    lower = message.lower()

    if any(keyword in lower for keyword in _APY_KEYWORDS):
        return "OPTIMIZE_APY"
    if any(keyword in lower for keyword in _MONEY_KEYWORDS):
        return "OPTIMIZE_MONEY"
    if any(keyword in lower for keyword in _BTC_KEYWORDS):
        return "GET_INTO_BTC"
    if any(keyword in lower for keyword in _GENERIC_INVEST_KEYWORDS):
        return "GET_INTO_BTC"
    return "UNKNOWN"
