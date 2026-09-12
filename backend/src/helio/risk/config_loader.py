from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class RiskConfig(BaseModel):
    model_config = {"extra": "forbid"}

    allow_live: bool = False
    allowed_instrument_types: list[str] = ["SPOT"]
    allowed_instruments: list[str] = []
    max_order_notional_usd: float = 100
    max_position_size_usd: float = 500
    max_open_positions: int = 5
    max_leverage: float = 3
    max_daily_loss_usd: float = 50
    exposure_cap_pct_of_equity: float = 20
    require_stop_loss_rationale: bool = False


def load_risk_config(path: Path) -> RiskConfig:
    if not path.exists():
        raise FileNotFoundError(
            f"Risk config not found at {path}. Copy "
            "backend/config/risk_config.example.yaml to that path and adjust it."
        )
    with path.open() as fh:
        raw = yaml.safe_load(fh) or {}
    return RiskConfig.model_validate(raw)
