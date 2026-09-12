from __future__ import annotations

from helio.guard.config import GuardConfig
from helio.guard.context import GuardContext
from helio.guard.rules import ALL_RULES
from helio.schemas.guard import GuardCheck, GuardDecision, GuardRiskSummary, GuardTradeIntent


class GuardEngine:
    """The deterministic gate between a Thesis-derived TradeIntent and OKX
    execution. No LLM. Fails CLOSED: any rule that raises an unexpected
    exception (an "unknown risk condition") is treated as a FAIL, not
    swallowed into an approval — the engine never crashes into a decision,
    and it never assumes an unverifiable condition is safe.
    """

    def __init__(self, config: GuardConfig):
        self._config = config

    @property
    def config(self) -> GuardConfig:
        return self._config

    def evaluate(self, intent: GuardTradeIntent, ctx: GuardContext) -> GuardDecision:
        checks: list[GuardCheck] = []
        for rule in ALL_RULES:
            try:
                checks.append(rule(intent, ctx, self._config))
            except Exception as exc:  # noqa: BLE001 - deliberate fail-closed catch-all
                checks.append(
                    GuardCheck(
                        name=rule.__name__,
                        status="FAIL",
                        reason=f"unknown risk condition: {rule.__name__} raised {exc.__class__.__name__}: {exc}",
                    )
                )

        rejection_reasons = [c.reason for c in checks if c.status == "FAIL"]
        approved = len(rejection_reasons) == 0

        risk_summary = self._risk_summary(intent, ctx)

        return GuardDecision(
            decision="APPROVE" if approved else "REJECT",
            trade_intent_id=intent.trade_intent_id,
            checks=checks,
            risk_summary=risk_summary,
            rejection_reasons=rejection_reasons,
            policy_version=self._config.policy_version,
        )

    def _risk_summary(self, intent: GuardTradeIntent, ctx: GuardContext) -> GuardRiskSummary:
        try:
            requested_notional = float(intent.requested_notional)
        except (ValueError, TypeError):
            requested_notional = 0.0

        estimated_loss = None
        risk_reward = None
        try:
            if intent.invalidation and intent.invalidation.price:
                entry = float(intent.entry_price)
                stop = float(intent.invalidation.price)
                qty = float(intent.requested_quantity)
                estimated_loss = max(entry - stop, 0.0) * qty
                if intent.target and intent.target.price:
                    target = float(intent.target.price)
                    risk = entry - stop
                    reward = target - entry
                    if risk > 0:
                        risk_reward = reward / risk
        except (ValueError, TypeError, ZeroDivisionError):
            pass

        return GuardRiskSummary(
            requested_notional=requested_notional,
            max_allowed_notional=self._config.max_notional_per_trade_usd,
            estimated_loss=estimated_loss,
            risk_reward=risk_reward,
        )
