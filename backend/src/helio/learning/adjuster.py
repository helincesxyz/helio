from __future__ import annotations

from pydantic import BaseModel

from helio.schemas.events import LearningEvent


class AdjustmentSuggestion(BaseModel):
    model_config = {"extra": "forbid"}

    strategy_id: str
    suggestion: str
    rationale: str


class ParameterAdjuster:
    """v1: NOT IMPLEMENTED.

    This interface exists so a future version of Helio can compute
    advisory strategy-parameter suggestions (e.g. "win rate over the last
    50 trades is low, consider reducing order_notional_usd") from the
    EventStore's history. `suggest_adjustments` always returns None today.

    Any future implementation MUST remain advisory-only: it may propose a
    suggestion for a human (or an LLM operator) to review, but it must
    never write directly to risk_config.yaml or strategy_config.yaml.
    Automatically tightening or loosening risk limits without human review
    defeats the purpose of having a deterministic risk gate at all.
    """

    def suggest_adjustments(
        self, strategy_id: str, history: list[LearningEvent]
    ) -> AdjustmentSuggestion | None:
        return None
