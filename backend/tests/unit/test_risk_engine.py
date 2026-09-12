from __future__ import annotations

from helio.risk.engine import RiskEngine


def test_engine_approves_intent_within_all_limits(make_intent, make_account, risk_config):
    engine = RiskEngine(risk_config)
    decision = engine.evaluate(make_intent(), make_account())
    assert decision.approved is True
    assert decision.violated_rules == []
    assert decision.reasons == ["within all limits"]


def test_engine_rejects_and_lists_all_violated_rules(make_intent, make_account, risk_config):
    engine = RiskEngine(risk_config)
    intent = make_intent(mode="live", symbol="DOGE-USDT", leverage="10")
    decision = engine.evaluate(intent, make_account())
    assert decision.approved is False
    assert "sim_vs_live_gate" in decision.violated_rules
    assert "allowed_instrument" in decision.violated_rules
    assert "max_leverage" in decision.violated_rules
    assert len(decision.reasons) == len(decision.violated_rules)


def test_engine_never_raises_on_business_rejection(make_intent, make_account, risk_config):
    engine = RiskEngine(risk_config)
    # Should not raise even for a maximally-violating intent.
    intent = make_intent(mode="live", instrument_type="FUTURES", symbol="DOGE-USDT", size="99999", leverage="99")
    decision = engine.evaluate(intent, make_account())
    assert decision.approved is False


def test_engine_decision_carries_stable_config_hash(make_intent, make_account, risk_config):
    engine = RiskEngine(risk_config)
    d1 = engine.evaluate(make_intent(), make_account())
    d2 = engine.evaluate(make_intent(), make_account())
    assert d1.risk_config_hash == d2.risk_config_hash
