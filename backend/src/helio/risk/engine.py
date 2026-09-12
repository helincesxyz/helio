from __future__ import annotations

import hashlib

from helio.risk.config_loader import RiskConfig
from helio.risk.rules import ALL_RULES
from helio.schemas.account import AccountState
from helio.schemas.risk_decision import RiskDecision
from helio.schemas.trade_intent import TradeIntent


def _config_hash(config: RiskConfig) -> str:
    return hashlib.sha256(config.model_dump_json().encode()).hexdigest()[:16]


class RiskEngine:
    """The deterministic gate between any TradeIntent and OKX execution.

    Never raises on a business rejection — a rejected intent is a normal,
    expected outcome represented by `RiskDecision.approved is False`. It only
    raises on malformed input (a bug), which should surface loudly.
    """

    def __init__(self, config: RiskConfig):
        self._config = config
        self._config_hash = _config_hash(config)

    @property
    def config(self) -> RiskConfig:
        return self._config

    def evaluate(self, intent: TradeIntent, account: AccountState) -> RiskDecision:
        results = [rule(intent, account, self._config) for rule in ALL_RULES]
        violated = [r.rule for r in results if not r.passed]
        approved = len(violated) == 0
        reasons = [r.reason for r in results if not r.passed] or ["within all limits"]
        return RiskDecision(
            intent_id=intent.intent_id,
            approved=approved,
            reasons=reasons,
            violated_rules=violated,
            risk_config_hash=self._config_hash,
            computed={},
        )
