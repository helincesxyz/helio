"""Deterministic guard rules — the safety policy between a Thesis-derived
trade intent and OKX execution. No LLM anywhere in this module. Every rule
has the signature `(intent, ctx, config) -> GuardCheck` and fails CLOSED:
when something needed to prove safety is missing, stale, malformed, or
unverifiable, the rule returns FAIL — it never assumes an unknown condition
is safe.
"""
from __future__ import annotations

from helio.guard.context import GuardContext
from helio.guard.config import GuardConfig
from helio.schemas.guard import GuardCheck, GuardTradeIntent

CONFIDENCE_TOLERANCE = 1e-6
NUMERIC_TOLERANCE_PCT = 0.1  # matches thesis/decision_quality.py's hallucination tolerance


def _pass(name: str, reason: str) -> GuardCheck:
    return GuardCheck(name=name, status="PASS", reason=reason)


def _fail(name: str, reason: str) -> GuardCheck:
    return GuardCheck(name=name, status="FAIL", reason=reason)


def check_allowed_symbol(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "allowed_symbol"
    if intent.symbol not in config.allowed_symbols:
        return _fail(name, f"{intent.symbol} is not in the allowed symbol list {config.allowed_symbols}")
    return _pass(name, f"{intent.symbol} is allowed")


def check_spot_only(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "spot_only"
    if intent.instrument_type not in config.allowed_instrument_types:
        return _fail(name, f"instrument_type {intent.instrument_type} is not spot — derivatives are not permitted")
    return _pass(name, "instrument is spot")


def check_no_leverage(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "no_leverage"
    if intent.leverage is None:
        return _pass(name, "no leverage requested")
    try:
        lev = float(intent.leverage)
    except ValueError:
        return _fail(name, f"leverage {intent.leverage!r} is not a valid number")
    if lev > config.max_leverage:
        return _fail(name, f"requested leverage {lev} exceeds max_leverage {config.max_leverage}")
    return _pass(name, "leverage within policy")


def check_no_short(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "no_short"
    if intent.side not in config.allowed_sides:
        return _fail(name, f"side {intent.side!r} is not permitted — shorting is not allowed in v1")
    return _pass(name, "side is long/buy only")


def check_max_position(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "max_position"
    if ctx.account is None:
        return _fail(name, "cannot verify current position: no account state available")
    open_count = 0
    for pos in ctx.account.positions:
        if pos.instId != intent.symbol:
            continue
        if abs(float(pos.pos)) > 0:
            open_count += 1
    if open_count >= config.max_simultaneous_positions:
        return _fail(
            name,
            f"{open_count} open {intent.symbol} position(s) already exist; "
            f"max_simultaneous_positions is {config.max_simultaneous_positions}",
        )
    return _pass(name, f"{open_count} open position(s), within limit {config.max_simultaneous_positions}")


def check_max_notional(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "max_notional"
    try:
        notional = float(intent.requested_notional)
    except ValueError:
        return _fail(name, f"requested_notional {intent.requested_notional!r} is not a valid number")
    if notional <= 0:
        return _fail(name, f"requested_notional {notional} must be positive")
    if notional > config.max_notional_per_trade_usd:
        return _fail(name, f"requested notional ${notional:.2f} exceeds max_notional_per_trade_usd ${config.max_notional_per_trade_usd:.2f}")
    return _pass(name, f"requested notional ${notional:.2f} within limit")


def check_daily_loss(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "daily_loss_limit"
    if ctx.account is None:
        return _fail(name, "cannot verify daily PnL: no account state available")
    if ctx.account.daily_realized_pnl_usd is None:
        return _fail(name, "cannot verify daily PnL: account state does not report daily_realized_pnl_usd")
    try:
        pnl = float(ctx.account.daily_realized_pnl_usd)
    except ValueError:
        return _fail(name, f"daily_realized_pnl_usd {ctx.account.daily_realized_pnl_usd!r} is not a valid number")
    if pnl < 0 and abs(pnl) >= config.max_daily_loss_usd:
        return _fail(name, f"daily realized loss ${abs(pnl):.2f} has reached max_daily_loss_usd ${config.max_daily_loss_usd:.2f}")
    return _pass(name, "daily loss within limit")


def check_exposure(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "portfolio_exposure"
    if ctx.account is None:
        return _fail(name, "cannot verify portfolio exposure: no account state available")
    equity = 0.0
    for bal in ctx.account.balances:
        if bal.ccy.upper() in ("USD", "USDT", "USDC"):
            equity += float(bal.total)
    if equity <= 0:
        return _fail(name, "cannot verify portfolio exposure: no USD/USDT/USDC equity reported")
    existing_exposure = sum(abs(float(p.pos)) * float(p.avgPx) for p in ctx.account.positions if p.pos and p.avgPx)
    notional = float(intent.requested_notional)
    projected_pct = (existing_exposure + notional) / equity * 100
    if projected_pct > config.max_portfolio_exposure_pct:
        return _fail(name, f"projected exposure {projected_pct:.1f}% of equity exceeds cap {config.max_portfolio_exposure_pct}%")
    return _pass(name, f"projected exposure {projected_pct:.1f}% within cap")


def check_invalidation_valid(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "invalidation_defined"
    if intent.invalidation is None or not intent.invalidation.condition.strip():
        return _fail(name, "a BUY requires a non-empty invalidation condition")
    if intent.invalidation.price is None:
        return _fail(name, "invalidation must include a stop price")
    try:
        stop = float(intent.invalidation.price)
        entry = float(intent.entry_price)
    except ValueError:
        return _fail(name, "invalidation price or entry price is not a valid number")
    if stop >= entry:
        return _fail(name, f"invalid stop: invalidation price {stop} must be below entry price {entry} for a long")
    return _pass(name, f"invalidation at {stop} is below entry {entry}")


def check_risk_reward(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "risk_reward"
    if intent.invalidation is None or intent.invalidation.price is None:
        return _fail(name, "cannot compute risk/reward without a valid invalidation price")
    if intent.target is None or intent.target.price is None:
        return _fail(name, "cannot compute risk/reward without a target price")
    entry = float(intent.entry_price)
    stop = float(intent.invalidation.price)
    target = float(intent.target.price)
    risk = entry - stop
    reward = target - entry
    if risk <= 0:
        return _fail(name, f"invalid stop: risk distance is {risk} (must be positive)")
    if reward <= 0:
        return _fail(name, f"target {target} is not above entry {entry} — no reward")
    rr = reward / risk
    if rr < config.min_risk_reward:
        return _fail(name, f"risk/reward {rr:.2f} is below minimum {config.min_risk_reward}")
    return _pass(name, f"risk/reward {rr:.2f} meets minimum {config.min_risk_reward}")


def check_market_data_fresh(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "market_data_fresh"
    if ctx.thesis_record is None:
        return _fail(name, "cannot verify market data freshness: linked thesis not found")
    age = (ctx.now - ctx.thesis_record.prepared_state.prepared_at).total_seconds()
    if age > config.max_market_data_age_seconds:
        return _fail(name, f"market data is {age:.0f}s old, exceeds max_market_data_age_seconds {config.max_market_data_age_seconds}")
    return _pass(name, f"market data is {age:.0f}s old, within freshness window")


def check_account_state_verifiable(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "account_state_verifiable"
    if ctx.account is None:
        return _fail(name, "account state could not be verified — no state provided")
    age = (ctx.now - ctx.account.as_of).total_seconds()
    if age > config.max_account_state_age_seconds:
        return _fail(name, f"account state is {age:.0f}s old, exceeds max_account_state_age_seconds {config.max_account_state_age_seconds}")
    return _pass(name, f"account state is {age:.0f}s old, verifiable")


def check_thesis_found(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "thesis_found"
    if ctx.thesis_record is None:
        return _fail(name, f"no thesis found for thesis_id {intent.thesis_id!r}")
    if ctx.thesis_record.decision_id != intent.thesis_id:
        return _fail(name, "resolved thesis decision_id does not match intent.thesis_id")
    return _pass(name, "thesis found and linked")


def check_thesis_not_wait(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "thesis_action_not_wait"
    if ctx.thesis_record is None:
        return _fail(name, "cannot verify thesis action: thesis not found")
    if ctx.thesis_record.thesis.action != "BUY":
        return _fail(name, f"linked thesis action is {ctx.thesis_record.thesis.action!r} — a WAIT thesis must never reach execution")
    return _pass(name, "linked thesis action is BUY")


def check_thesis_valid(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "thesis_result_valid"
    if ctx.thesis_record is None:
        return _fail(name, "cannot verify thesis validity: thesis not found")
    if not ctx.thesis_record.validation.valid:
        return _fail(name, f"linked thesis failed its own decision-quality validation: {ctx.thesis_record.validation.errors}")
    return _pass(name, "linked thesis passed decision-quality validation")


def check_thesis_symbol_matches(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "thesis_symbol_matches"
    if ctx.thesis_record is None:
        return _fail(name, "cannot verify symbol match: thesis not found")
    if ctx.thesis_record.thesis.symbol != intent.symbol:
        return _fail(name, f"intent symbol {intent.symbol} does not match thesis symbol {ctx.thesis_record.thesis.symbol}")
    return _pass(name, "intent symbol matches linked thesis")


def check_confidence_matches_thesis(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "confidence_matches_thesis"
    if ctx.thesis_record is None:
        return _fail(name, "cannot verify confidence: thesis not found")
    thesis_conf = ctx.thesis_record.thesis.confidence
    if abs(intent.confidence - thesis_conf) > CONFIDENCE_TOLERANCE:
        return _fail(name, f"intent confidence {intent.confidence} does not match linked thesis confidence {thesis_conf}")
    return _pass(name, "intent confidence matches linked thesis")


def check_min_confidence(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "min_confidence"
    if intent.confidence < config.min_confidence:
        return _fail(name, f"confidence {intent.confidence} is below min_confidence {config.min_confidence}")
    return _pass(name, f"confidence {intent.confidence} meets min_confidence {config.min_confidence}")


def check_well_formed(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "well_formed"
    try:
        notional = float(intent.requested_notional)
        qty = float(intent.requested_quantity)
        price = float(intent.entry_price)
    except ValueError:
        return _fail(name, "one or more numeric fields are not valid numbers")
    if notional <= 0 or qty <= 0 or price <= 0:
        return _fail(name, "requested_notional, requested_quantity, and entry_price must all be positive")
    if not intent.strategy or not intent.strategy_version or not intent.thesis_id:
        return _fail(name, "strategy, strategy_version, and thesis_id must all be non-empty")
    return _pass(name, "trade intent is well-formed")


def check_duplicate(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "not_duplicate"
    if ctx.is_duplicate:
        return _fail(name, f"a trade intent for thesis_id {intent.thesis_id!r} has already been evaluated")
    return _pass(name, "not a duplicate")


def check_quantity_precision(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "quantity_precision"
    try:
        qty = float(intent.requested_quantity)
        lot = float(config.lot_size)
    except ValueError:
        return _fail(name, "requested_quantity or lot_size is not a valid number")
    if lot <= 0:
        return _fail(name, "invalid lot_size configuration")
    # qty must be an exact integer multiple of the lot size; a relative
    # tolerance here only absorbs float representation error, not "close
    # enough" rounding (rounding to the nearest multiple would trivially
    # always pass, which defeats the point of this check).
    ratio = qty / lot
    nearest_int = round(ratio)
    if abs(ratio - nearest_int) > 1e-6:
        return _fail(name, f"requested_quantity {qty} is not a multiple of the exchange lot size {lot}")
    return _pass(name, f"requested_quantity {qty} conforms to lot size {lot}")


def check_quantity_minimum(intent: GuardTradeIntent, ctx: GuardContext, config: GuardConfig) -> GuardCheck:
    name = "quantity_minimum"
    try:
        qty = float(intent.requested_quantity)
        min_size = float(config.min_size)
    except ValueError:
        return _fail(name, "requested_quantity or min_size is not a valid number")
    if qty < min_size:
        return _fail(name, f"requested_quantity {qty} is below the exchange minimum size {min_size}")
    return _pass(name, f"requested_quantity {qty} meets minimum size {min_size}")


ALL_RULES = [
    check_well_formed,
    check_allowed_symbol,
    check_spot_only,
    check_no_leverage,
    check_no_short,
    check_thesis_found,
    check_thesis_not_wait,
    check_thesis_valid,
    check_thesis_symbol_matches,
    check_confidence_matches_thesis,
    check_min_confidence,
    check_market_data_fresh,
    check_account_state_verifiable,
    check_max_position,
    check_max_notional,
    check_exposure,
    check_daily_loss,
    check_invalidation_valid,
    check_risk_reward,
    check_quantity_precision,
    check_quantity_minimum,
    check_duplicate,
]
