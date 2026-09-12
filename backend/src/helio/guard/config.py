from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

POLICY_VERSION = "guard_v1"


class GuardConfig(BaseModel):
    model_config = {"extra": "forbid"}

    policy_version: str = POLICY_VERSION

    allowed_symbols: list[str] = ["BTC-USDT"]
    allowed_instrument_types: list[str] = ["SPOT"]
    max_leverage: float = 1.0
    allowed_sides: list[str] = ["buy"]  # no shorting in v1
    max_simultaneous_positions: int = 1

    max_notional_per_trade_usd: float = 100.0
    max_daily_loss_usd: float = 50.0
    max_portfolio_exposure_pct: float = 20.0
    min_risk_reward: float = 1.5
    min_confidence: float = 0.6

    max_market_data_age_seconds: int = 900  # 15 minutes
    max_account_state_age_seconds: int = 900

    # BTC-USDT spot instrument spec, confirmed live via market_get_instruments
    # (lotSz/minSz as of the last check — revalidate periodically, these are
    # not expected to change often but are exchange-controlled, not Helio's).
    lot_size: str = "0.00000001"
    min_size: str = "0.00001"


def load_guard_config(path: Path) -> GuardConfig:
    if not path.exists():
        raise FileNotFoundError(
            f"Guard config not found at {path}. Copy "
            "backend/config/guard_config.example.yaml to that path and adjust it."
        )
    with path.open() as fh:
        raw = yaml.safe_load(fh) or {}
    return GuardConfig.model_validate(raw)
