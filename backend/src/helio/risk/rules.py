"""Individual, pure risk rules.

Every rule has the signature `(intent, account, config) -> RuleResult` and is
a pure function: no I/O, no wall-clock reads beyond what's already on the
input objects, deterministic given the same inputs. When a rule cannot
determine a value it needs (e.g. no price to compute notional), it fails
closed (rejects) rather than guessing — this is a safety gate, not a
best-effort estimator.
"""
from __future__ import annotations

from helio.risk.config_loader import RiskConfig
from helio.schemas.account import AccountState
from helio.schemas.risk_decision import RuleResult
from helio.schemas.trade_intent import TradeIntent


def _estimate_notional_usd(intent: TradeIntent) -> float | None:
    """Best-effort, fail-closed notional estimate in USD-equivalent terms."""
    try:
        size = float(intent.size)
    except ValueError:
        return None

    if intent.size_unit == "quote_ccy":
        return size
    if intent.size_unit == "base_ccy":
        if intent.price is None:
            return None
        return size * float(intent.price)
    # "contracts": notional depends on contract multiplier, which Helio does
    # not know without an instrument spec — cannot be safely estimated in v1.
    return None


def check_sim_vs_live_gate(intent: TradeIntent, account: AccountState, config: RiskConfig) -> RuleResult:
    if intent.mode == "live" and not config.allow_live:
        return RuleResult(
            rule="sim_vs_live_gate",
            passed=False,
            reason="intent.mode is 'live' but risk_config.allow_live is False",
        )
    return RuleResult(rule="sim_vs_live_gate", passed=True, reason="mode/allow_live consistent")


def check_allowed_instrument_type(intent: TradeIntent, account: AccountState, config: RiskConfig) -> RuleResult:
    if intent.instrument_type not in config.allowed_instrument_types:
        return RuleResult(
            rule="allowed_instrument_type",
            passed=False,
            reason=f"{intent.instrument_type} not in allowed_instrument_types {config.allowed_instrument_types}",
        )
    return RuleResult(rule="allowed_instrument_type", passed=True, reason="instrument type allowed")


def check_allowed_instrument(intent: TradeIntent, account: AccountState, config: RiskConfig) -> RuleResult:
    if config.allowed_instruments and intent.symbol not in config.allowed_instruments:
        return RuleResult(
            rule="allowed_instrument",
            passed=False,
            reason=f"{intent.symbol} not in allowed_instruments {config.allowed_instruments}",
        )
    return RuleResult(rule="allowed_instrument", passed=True, reason="instrument allowed")


def check_max_order_notional(intent: TradeIntent, account: AccountState, config: RiskConfig) -> RuleResult:
    notional = _estimate_notional_usd(intent)
    if notional is None:
        return RuleResult(
            rule="max_order_notional",
            passed=False,
            reason="cannot compute order notional (need price for base_ccy size, or size_unit=quote_ccy)",
        )
    if notional > config.max_order_notional_usd:
        return RuleResult(
            rule="max_order_notional",
            passed=False,
            reason=f"order notional ${notional:.2f} exceeds max_order_notional_usd ${config.max_order_notional_usd:.2f}",
        )
    return RuleResult(rule="max_order_notional", passed=True, reason=f"order notional ${notional:.2f} within limit")


def check_max_position_size(intent: TradeIntent, account: AccountState, config: RiskConfig) -> RuleResult:
    notional = _estimate_notional_usd(intent)
    if notional is None:
        return RuleResult(
            rule="max_position_size",
            passed=False,
            reason="cannot compute projected position size without order notional",
        )
    existing = 0.0
    for pos in account.positions:
        if pos.instId == intent.symbol:
            try:
                existing += abs(float(pos.pos)) * float(pos.avgPx)
            except ValueError:
                pass
    projected = existing + notional
    if projected > config.max_position_size_usd:
        return RuleResult(
            rule="max_position_size",
            passed=False,
            reason=f"projected position ${projected:.2f} exceeds max_position_size_usd ${config.max_position_size_usd:.2f}",
        )
    return RuleResult(rule="max_position_size", passed=True, reason=f"projected position ${projected:.2f} within limit")


def check_max_open_positions(intent: TradeIntent, account: AccountState, config: RiskConfig) -> RuleResult:
    open_symbols = {p.instId for p in account.positions if float(p.pos or 0) != 0}
    is_new_position = intent.symbol not in open_symbols
    if is_new_position and len(open_symbols) + 1 > config.max_open_positions:
        return RuleResult(
            rule="max_open_positions",
            passed=False,
            reason=f"opening {intent.symbol} would exceed max_open_positions {config.max_open_positions}",
        )
    return RuleResult(rule="max_open_positions", passed=True, reason="open position count within limit")


def check_max_leverage(intent: TradeIntent, account: AccountState, config: RiskConfig) -> RuleResult:
    if intent.leverage is None:
        return RuleResult(rule="max_leverage", passed=True, reason="no leverage requested")
    if float(intent.leverage) > config.max_leverage:
        return RuleResult(
            rule="max_leverage",
            passed=False,
            reason=f"requested leverage {intent.leverage} exceeds max_leverage {config.max_leverage}",
        )
    return RuleResult(rule="max_leverage", passed=True, reason="leverage within limit")


def check_max_daily_loss(intent: TradeIntent, account: AccountState, config: RiskConfig) -> RuleResult:
    if account.daily_realized_pnl_usd is None:
        return RuleResult(rule="max_daily_loss", passed=True, reason="no daily PnL data available")
    pnl = float(account.daily_realized_pnl_usd)
    if pnl < 0 and abs(pnl) >= config.max_daily_loss_usd:
        return RuleResult(
            rule="max_daily_loss",
            passed=False,
            reason=f"daily realized loss ${abs(pnl):.2f} has reached max_daily_loss_usd ${config.max_daily_loss_usd:.2f}",
        )
    return RuleResult(rule="max_daily_loss", passed=True, reason="daily loss within limit")


def check_exposure_cap(intent: TradeIntent, account: AccountState, config: RiskConfig) -> RuleResult:
    equity = 0.0
    for bal in account.balances:
        if bal.ccy.upper() in ("USD", "USDT", "USDC"):
            try:
                equity += float(bal.total)
            except ValueError:
                pass
    if equity <= 0:
        return RuleResult(
            rule="exposure_cap",
            passed=False,
            reason="cannot compute exposure cap: no USD/USDT/USDC equity reported",
        )
    existing_exposure = sum(
        abs(float(p.pos)) * float(p.avgPx) for p in account.positions if p.pos and p.avgPx
    )
    notional = _estimate_notional_usd(intent) or 0.0
    projected_pct = (existing_exposure + notional) / equity * 100
    if projected_pct > config.exposure_cap_pct_of_equity:
        return RuleResult(
            rule="exposure_cap",
            passed=False,
            reason=f"projected exposure {projected_pct:.1f}% of equity exceeds cap {config.exposure_cap_pct_of_equity}%",
        )
    return RuleResult(rule="exposure_cap", passed=True, reason=f"projected exposure {projected_pct:.1f}% within cap")


ALL_RULES = [
    check_sim_vs_live_gate,
    check_allowed_instrument_type,
    check_allowed_instrument,
    check_max_order_notional,
    check_max_position_size,
    check_max_open_positions,
    check_max_leverage,
    check_max_daily_loss,
    check_exposure_cap,
]
