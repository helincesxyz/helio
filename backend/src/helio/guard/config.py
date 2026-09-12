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


RISK_PROFILE_NAMES = ("low", "balanced", "high")

# Fields a risk-preference profile may never change relative to the others.
# Only bounded numeric knobs (notional/daily-loss/exposure/confidence/
# risk-reward caps) may vary between tiers — everything that decides *what
# can be traded at all* must stay identical.
HARD_INVARIANT_FIELDS = (
    "allowed_symbols",
    "allowed_instrument_types",
    "max_leverage",
    "allowed_sides",
    "lot_size",
    "min_size",
)


def load_guard_profiles(config_dir: Path) -> dict[str, GuardConfig]:
    """Loads the three real, backend-enforced risk-preference profiles and
    asserts the hard-invariant guarantee above at startup — a real,
    testable safety check, not a comment. A profile that weakens a
    hard-invariant field raises immediately rather than silently letting a
    "risk preference" bypass Gate 3's actual safety rules."""
    profiles: dict[str, GuardConfig] = {}
    for name in RISK_PROFILE_NAMES:
        path = config_dir / f"guard_profile_{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(
                f"Guard profile not found at {path}. Copy "
                f"backend/config/guard_profile_{name}.example.yaml to that path and adjust it."
            )
        with path.open() as fh:
            raw = yaml.safe_load(fh) or {}
        profiles[name] = GuardConfig.model_validate(raw)

    reference_name = RISK_PROFILE_NAMES[0]
    reference = profiles[reference_name]
    for name in RISK_PROFILE_NAMES[1:]:
        for field_name in HARD_INVARIANT_FIELDS:
            if getattr(profiles[name], field_name) != getattr(reference, field_name):
                raise ValueError(
                    f"guard profile {name!r} differs from {reference_name!r} on hard-invariant "
                    f"field {field_name!r} — risk-preference profiles may only vary bounded "
                    "numeric knobs (notional/daily-loss/exposure/confidence/risk-reward caps), "
                    "never safety-critical fields."
                )
    return profiles
