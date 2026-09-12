from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from helio.guard.config import HARD_INVARIANT_FIELDS, RISK_PROFILE_NAMES, load_guard_profiles

REAL_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _write_profile(dir_: Path, name: str, **overrides) -> None:
    base = dict(
        policy_version="guard_v1_test",
        allowed_symbols=["BTC-USDT"],
        allowed_instrument_types=["SPOT"],
        max_leverage=1.0,
        allowed_sides=["buy"],
        max_simultaneous_positions=1,
        max_notional_per_trade_usd=100.0,
        max_daily_loss_usd=50.0,
        max_portfolio_exposure_pct=20.0,
        min_risk_reward=1.5,
        min_confidence=0.6,
        max_market_data_age_seconds=900,
        max_account_state_age_seconds=900,
        lot_size="0.00000001",
        min_size="0.00001",
    )
    base.update(overrides)
    (dir_ / f"guard_profile_{name}.yaml").write_text(yaml.safe_dump(base))


def test_real_shipped_example_profiles_load_and_satisfy_the_invariant():
    profiles = {}
    for name in RISK_PROFILE_NAMES:
        with (REAL_CONFIG_DIR / f"guard_profile_{name}.example.yaml").open() as fh:
            profiles[name] = yaml.safe_load(fh)
    for field in HARD_INVARIANT_FIELDS:
        values = {name: profiles[name][field] for name in RISK_PROFILE_NAMES}
        assert len(set(map(str, values.values()))) == 1, f"{field} differs across shipped profiles: {values}"


def test_load_guard_profiles_returns_all_three(tmp_path: Path):
    for name in RISK_PROFILE_NAMES:
        _write_profile(tmp_path, name)
    profiles = load_guard_profiles(tmp_path)
    assert set(profiles.keys()) == set(RISK_PROFILE_NAMES)


def test_bounded_knobs_may_differ(tmp_path: Path):
    _write_profile(tmp_path, "low", max_notional_per_trade_usd=25.0, min_confidence=0.75)
    _write_profile(tmp_path, "balanced", max_notional_per_trade_usd=100.0, min_confidence=0.6)
    _write_profile(tmp_path, "high", max_notional_per_trade_usd=250.0, min_confidence=0.55)

    profiles = load_guard_profiles(tmp_path)
    assert profiles["low"].max_notional_per_trade_usd == 25.0
    assert profiles["high"].max_notional_per_trade_usd == 250.0


@pytest.mark.parametrize("field,bad_value", [
    ("allowed_symbols", ["ETH-USDT"]),
    ("allowed_instrument_types", ["SWAP"]),
    ("max_leverage", 5.0),
    ("allowed_sides", ["buy", "sell"]),
    ("lot_size", "0.001"),
    ("min_size", "0.1"),
])
def test_hard_invariant_violation_raises(tmp_path: Path, field: str, bad_value):
    _write_profile(tmp_path, "low")
    _write_profile(tmp_path, "balanced")
    _write_profile(tmp_path, "high", **{field: bad_value})

    with pytest.raises(ValueError, match="hard-invariant"):
        load_guard_profiles(tmp_path)


def test_missing_profile_file_raises_file_not_found(tmp_path: Path):
    _write_profile(tmp_path, "low")
    _write_profile(tmp_path, "balanced")
    # "high" deliberately not written.
    with pytest.raises(FileNotFoundError):
        load_guard_profiles(tmp_path)
